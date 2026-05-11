"""RQ-задача: запустить Docker-контейнер агента и стримить events."""
from __future__ import annotations

import contextlib
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog
from portal_sdk.manifest import Manifest
from redis import Redis
from sqlalchemy import text

from portal_worker.config import get_settings
from portal_worker.db import make_engine, make_session_factory, revoke_ephemeral_token_in_db
from portal_worker.runner.docker_runner import (
    RunCancelled,
    RunTimeout,
    run_agent_container,
)
from portal_worker.runner.llm_runtime_config import LlmRuntimeConfig
from portal_worker.runner.output_verifier import (
    OutputMissingError,
    scan_output_dir,
    verify_outputs,
)

_BUILD_ROOT = Path("/var/portal-files/jobs")  # named volume — путь одинаков в worker и виден Docker daemon когда тот монтирует agent-контейнер. /tmp/ был неработоспособным в docker-in-docker setup (worker /tmp ≠ host /tmp).


def recover_orphaned_jobs() -> None:
    """На старте worker: все 'running' → 'failed' с error_code='worker_restart'."""  # noqa: RUF002
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    log = structlog.get_logger()
    with session_factory() as session:
        result = session.execute(text("""
            UPDATE jobs SET status='failed', error_code='worker_restart',
                            finished_at=:now
            WHERE status='running'
            RETURNING id
        """), {"now": datetime.now(UTC)})
        ids = [r[0] for r in result]
        session.commit()
    if ids:
        log.warning("recovered_orphaned_jobs", count=len(ids))
    # Cleanup stale working directories
    for stale in _BUILD_ROOT.glob("portal-job-*"):
        shutil.rmtree(stale, ignore_errors=True)
    engine.dispose()


def run_job(payload: dict | str) -> None:
    """Запустить указанный job. Финализирует через UPDATE при любом исходе.

    payload — dict с ключами job_id (и опционально ephemeral_token), либо
    str job_id для обратной совместимости.
    """
    if isinstance(payload, str):
        job_id = payload
        ephemeral_token: str | None = None
    else:
        job_id = payload["job_id"]
        ephemeral_token = payload.get("ephemeral_token")

    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    redis = Redis.from_url(str(settings.redis_url))
    log = structlog.get_logger().bind(job_id=job_id)
    vid = uuid.UUID(job_id)
    workdir = _BUILD_ROOT / f"portal-job-{vid}"
    llm_config: LlmRuntimeConfig | None = None

    try:
        # 1. Атомарный лок + загрузить joined-данные
        with session_factory() as session:
            row = session.execute(text("""
                UPDATE jobs j
                SET status='running', started_at=:now
                FROM agent_versions av, agents a
                WHERE j.id=:vid AND j.status='queued'
                  AND av.id=j.agent_version_id AND a.id=av.agent_id
                RETURNING j.params_jsonb, av.docker_image_tag, av.manifest_jsonb,
                          a.slug AS agent_slug
            """), {"vid": vid, "now": datetime.now(UTC)}).first()
            session.commit()
            if row is None:
                log.info("job_not_queued_or_missing")
                return
            manifest = Manifest.model_validate(row.manifest_jsonb)
            image_tag = row.docker_image_tag
            params = row.params_jsonb
            agent_slug = row.agent_slug  # noqa: F841 — available for future use

        # 1b. Построить LlmRuntimeConfig если manifest содержит runtime.llm
        raw_manifest = row.manifest_jsonb or {}
        runtime_llm = (raw_manifest.get("runtime") or {}).get("llm")
        if runtime_llm and ephemeral_token:
            llm_config = LlmRuntimeConfig(
                ephemeral_token=ephemeral_token,
                agents_network_name=settings.llm_agents_network_name,
                proxy_base_url=settings.llm_proxy_base_url,
            )

        # 2. Материализовать inputs из FileStore (local = читать с диска)  # noqa: RUF003
        input_src = settings.file_store_local_root / str(vid) / "input"
        output_target_dir = settings.file_store_local_root / str(vid) / "output"
        input_dir = workdir / "input"
        output_dir = workdir / "output"
        # Clean any stale workdir from prior crash on same host before fresh mkdir
        shutil.rmtree(workdir, ignore_errors=True)
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        if input_src.exists():
            for src in input_src.iterdir():
                dst = input_dir / src.name
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        params_path = workdir / "params.json"
        params_path.write_text(json.dumps(params))

        # 3. Docker run + стрим events
        seq_counter = 0

        def on_event(event: dict) -> None:  # type: ignore[type-arg]
            nonlocal seq_counter
            seq_counter += 1
            with session_factory() as s:
                s.execute(text("""
                    INSERT INTO job_events (job_id, seq, ts, event_type, payload_jsonb)
                    VALUES (:vid, :seq, :ts, :type, CAST(:p AS jsonb))
                """), {
                    "vid": vid, "seq": seq_counter,
                    "ts": datetime.now(UTC),
                    "type": event.get("type", "unknown"),
                    "p": json.dumps(event),
                })
                s.commit()
            redis.publish(
                f"job:{vid}",
                json.dumps({"seq": seq_counter, "event": event}),
            )

        timeout_s = manifest.runtime.limits.max_runtime_minutes * 60
        if timeout_s > settings.job_timeout_seconds:
            timeout_s = settings.job_timeout_seconds

        try:
            exit_code = run_agent_container(
                image_tag=image_tag,
                input_dir=input_dir,
                output_dir=output_dir,
                params_path=params_path,
                memory_mb=manifest.runtime.limits.max_memory_mb,
                cpu_cores=manifest.runtime.limits.max_cpu_cores,
                timeout_seconds=timeout_s,
                cancel_check=lambda: bool(redis.exists(f"job:{vid}:cancel")),
                on_event=on_event,
                labels={"portal-job": str(vid)},
                llm_config=llm_config,
            )
        except RunCancelled:
            _finalize(session_factory, vid, status="cancelled",
                      error_code="cancelled", error_msg=None)
            redis.publish(f"job:{vid}", json.dumps(
                {"seq": seq_counter + 1, "event": {"type": "failed", "msg": "cancelled"}}
            ))
            return
        except RunTimeout as exc:
            _finalize(session_factory, vid, status="failed",
                      error_code="timeout", error_msg=str(exc))
            return

        # 4. Verify outputs объявленных в manifest
        declared = [o.filename for o in manifest.outputs]
        try:
            verify_outputs(output_dir, declared_filenames=declared)
        except OutputMissingError as exc:
            _finalize(session_factory, vid, status="failed",
                      error_code="output_missing", error_msg=str(exc))
            return

        # 5. Просканировать ВСЕ файлы → FileStore output + INSERT job_files  # noqa: RUF003
        produced = scan_output_dir(output_dir)
        total_size = sum(p.size_bytes for p in produced)
        if total_size > settings.max_job_output_bytes:
            _finalize(session_factory, vid, status="failed",
                      error_code="output_too_large",
                      error_msg=f"total {total_size} > limit {settings.max_job_output_bytes}")
            return

        output_target_dir.mkdir(parents=True, exist_ok=True)
        with session_factory() as session:
            for f in produced:
                target = output_target_dir / f.relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f.absolute_path, target)
                session.execute(text("""
                    INSERT INTO job_files (job_id, kind, filename, size_bytes,
                                            sha256, storage_key)
                    VALUES (:vid, 'output', :name, :size, :sha, :key)
                    ON CONFLICT (job_id, kind, filename) DO UPDATE
                    SET size_bytes=EXCLUDED.size_bytes, sha256=EXCLUDED.sha256
                """), {
                    "vid": vid, "name": f.relative_path,
                    "size": f.size_bytes, "sha": f.sha256,
                    "key": f"{vid}/output/{f.relative_path}",
                })
            session.commit()

        # 6. Finalize
        _finalize(session_factory, vid, status="ready", exit_code=exit_code)

    except Exception as exc:
        log.error("run_job_unexpected", exc_info=True)
        _finalize(session_factory, vid, status="failed",
                  error_code="docker_error", error_msg=str(exc))
    finally:
        if llm_config is not None:
            with contextlib.suppress(Exception):
                revoke_ephemeral_token_in_db(vid)
        shutil.rmtree(workdir, ignore_errors=True)
        with contextlib.suppress(Exception):
            redis.delete(f"job:{vid}:cancel")
        with contextlib.suppress(Exception):
            redis.close()
        engine.dispose()


def _finalize(
    session_factory: object,
    vid: uuid.UUID,
    *,
    status: str,
    error_code: str | None = None,
    error_msg: str | None = None,
    exit_code: int | None = None,
) -> None:
    with session_factory() as session:  # type: ignore[operator]
        finished_at = datetime.now(UTC)
        session.execute(text("""
            UPDATE jobs SET status=:st, error_code=:ec, error_msg=:em,
                             exit_code=:exc, finished_at=:now,
                             output_summary_jsonb=COALESCE(
                                 (SELECT payload_jsonb FROM job_events
                                  WHERE job_id=:vid AND event_type='result'
                                  ORDER BY seq DESC LIMIT 1),
                                 output_summary_jsonb
                             )
            WHERE id=:vid
        """), {"st": status, "ec": error_code, "em": error_msg,
               "exc": exit_code, "now": finished_at, "vid": vid})

        # Email-уведомление если opt-in и job шёл достаточно долго.
        row = session.execute(text("""
            SELECT u.email, u.display_name, u.notify_on_job_finish,
                   a.name AS agent_name,
                   j.started_at
            FROM jobs j
            JOIN agent_versions av ON av.id = j.agent_version_id
            JOIN agents a ON a.id = av.agent_id
            JOIN users u ON u.id = j.created_by_user_id
            WHERE j.id = :vid
        """), {"vid": vid}).first()
        session.commit()

        if row and row.notify_on_job_finish:
            from portal_worker.config import get_settings as _gs
            from portal_worker.services.email import send_job_finished_email
            cfg = _gs()
            duration = 0
            if row.started_at:
                duration = max(0, int((finished_at - row.started_at).total_seconds()))
            if duration >= cfg.email_min_job_duration_seconds:
                send_job_finished_email(
                    user_email=row.email,
                    user_display_name=row.display_name,
                    agent_name=row.agent_name,
                    job_id=vid,
                    job_status=status,
                    duration_s=duration,
                    base_url=cfg.portal_public_base_url,
                    smtp_host=cfg.smtp_host,
                    smtp_port=cfg.smtp_port,
                    smtp_user=cfg.smtp_user,
                    smtp_password=cfg.smtp_password,
                    smtp_from=cfg.smtp_from,
                )
