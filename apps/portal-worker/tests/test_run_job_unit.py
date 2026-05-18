"""Unit tests for run_job: recover_orphaned_jobs + atomic lock + happy/failed flows.

E2E with real docker is in test_run_job_e2e.py (Task 18).
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer


def _insert_job(
    pg_container: PostgresContainer,
    status: str = "pending_build",
    agent_status: str = "ready",
    manifest: dict[str, Any] | None = None,
    sha: str = "a" * 40,
) -> Any:
    """Helper: вставить user/tab/agent/agent_version/job."""
    if manifest is None:
        manifest = {
            "id": "x", "name": "X", "version": "0.1.0",
            "category": "научная-работа", "short_description": "d",
            "inputs": {}, "files": {},
            "outputs": [{"id": "o", "type": "any", "label": "o", "filename": "out.txt"}],
            "runtime": {
                "docker": {
                    "base_image": "python:3.12-slim",
                    "setup": [], "entrypoint": ["python", "agent.py"],
                },
                "llm": {"provider": "openrouter", "models": []},
                "limits": {"max_runtime_minutes": 1, "max_memory_mb": 128, "max_cpu_cores": 1},
            },
        }
    eng = create_engine(pg_container.get_connection_url())
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES (:e, 'h', 'd') RETURNING id"
        ), {"e": f"u-{sha[:6]}@example.com"}).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES (:s, 'T') RETURNING id"
        ), {"s": f"tab-{sha[:6]}"}).scalar_one()
        aid = c.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES (:s, 'A', 'd', :tid, 'https://x', :uid) RETURNING id"
        ), {"s": f"a-{sha[:6]}", "tid": tid, "uid": uid}).scalar_one()
        vid = c.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, docker_image_tag, "
            "created_by_user_id) "
            "VALUES (:aid, :sha, 'main', CAST(:m AS jsonb), '1.0', :st, :tag, :uid) "
            "RETURNING id"
        ), {"aid": aid, "sha": sha, "m": json.dumps(manifest),
            "st": agent_status, "tag": "portal/test:t1", "uid": uid}).scalar_one()
        jid = c.execute(text(
            "INSERT INTO jobs (agent_version_id, created_by_user_id, status, params_jsonb) "
            "VALUES (:vid, :uid, :st, '{}') RETURNING id"
        ), {"vid": vid, "uid": uid, "st": status}).scalar_one()
    eng.dispose()
    return jid


def test_recover_orphaned_jobs_marks_running_as_failed(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    from portal_worker.tasks.run_job import recover_orphaned_jobs
    jid = _insert_job(pg_container, status="running")
    recover_orphaned_jobs()
    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        row = c.execute(text(
            "SELECT status, error_code, finished_at FROM jobs WHERE id=:vid"
        ), {"vid": jid}).one()
    eng.dispose()
    assert row.status == "failed"
    assert row.error_code == "worker_restart"
    assert row.finished_at is not None


def test_recover_does_not_touch_other_statuses(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    from portal_worker.tasks.run_job import recover_orphaned_jobs
    jid = _insert_job(pg_container, status="ready", sha="b" * 40)
    recover_orphaned_jobs()
    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        st = c.execute(text("SELECT status FROM jobs WHERE id=:vid"),
                       {"vid": jid}).scalar_one()
    eng.dispose()
    assert st == "ready"


def test_run_job_skips_if_not_queued(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    """Job уже в running (race) — не делаем ничего."""
    from portal_worker.tasks.run_job import run_job
    jid = _insert_job(pg_container, status="running", sha="c" * 40)
    run_job(str(jid))  # должен тихо выйти
    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        st = c.execute(text("SELECT status FROM jobs WHERE id=:vid"),
                       {"vid": jid}).scalar_one()
    eng.dispose()
    assert st == "running"  # не тронут


def test_run_job_failed_finalize_on_run_exception(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    """Если run_agent_container бросает исключение — job='failed'."""
    from portal_worker.tasks import run_job as mod
    jid = _insert_job(pg_container, status="queued", sha="d" * 40)

    with patch.object(mod, "run_agent_container",
                      side_effect=RuntimeError("oops")):
        mod.run_job(str(jid))

    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        row = c.execute(text(
            "SELECT status, error_code, error_msg FROM jobs WHERE id=:vid"
        ), {"vid": jid}).one()
    eng.dispose()
    assert row.status == "failed"
    assert row.error_code == "docker_error"
    assert "oops" in row.error_msg


def test_run_job_agent_crashed_surfaces_stderr(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    """Агент упал (exit!=0): job=failed, error_code=agent_crashed,
    stderr-хвост виден — НЕ немой output_missing."""
    from portal_worker.runner.docker_runner import RunResult
    from portal_worker.tasks import run_job as mod
    jid = _insert_job(pg_container, status="queued", sha="e" * 40)

    with patch.object(mod, "run_agent_container",
                      return_value=RunResult(exit_code=2,
                                             stderr_tail="Traceback ... BOOM_4477")):
        mod.run_job(str(jid))

    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        row = c.execute(text(
            "SELECT status, error_code, error_msg FROM jobs WHERE id=:vid"
        ), {"vid": jid}).one()
    eng.dispose()
    assert row.status == "failed"
    assert row.error_code == "agent_crashed"
    assert "BOOM_4477" in row.error_msg
    assert "кодом 2" in row.error_msg


def test_run_job_input_missing_when_required_file_not_uploaded(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    """Сценарий препода: folder-агент запущен без файлов. Серверная
    проверка required → понятный input_missing ДО запуска контейнера,
    не немой output_missing."""
    from portal_worker.tasks import run_job as mod
    manifest = {
        "id": "x", "name": "X", "version": "0.1.0",
        "category": "научная-работа", "short_description": "d",
        "inputs": {},
        "files": {"papers": {"type": "folder", "label": "Папка статей",
                              "required": True}},
        "outputs": [{"id": "o", "type": "any", "label": "o", "filename": "out.txt"}],
        "runtime": {
            "docker": {"base_image": "python:3.12-slim", "setup": [],
                       "entrypoint": ["python", "agent.py"]},
            "llm": {"provider": "openrouter", "models": []},
            "limits": {"max_runtime_minutes": 1, "max_memory_mb": 128,
                       "max_cpu_cores": 1},
        },
    }
    jid = _insert_job(pg_container, status="queued", sha="f" * 40,
                      manifest=manifest)

    called = {"n": 0}

    def _should_not_run(**_kw):
        called["n"] += 1
        raise AssertionError("контейнер не должен запускаться")

    with patch.object(mod, "run_agent_container", _should_not_run):
        mod.run_job(str(jid))

    assert called["n"] == 0
    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        row = c.execute(text(
            "SELECT status, error_code, error_msg FROM jobs WHERE id=:v"
        ), {"v": jid}).one()
    eng.dispose()
    assert row.status == "failed"
    assert row.error_code == "input_missing"
    assert "Папка статей" in row.error_msg
