"""Простой scheduler: каждые 60с проверяет cron_jobs.next_run_at и enqueue jobs.

Сделан без rq-scheduler и без crontab parsing — 4 пресета (hourly/daily/
weekly/monthly), достаточно для демо-уровня и хорошо предсказуемо.

Запускается отдельным daemon-thread из main().
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from rq import Queue
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

log = structlog.get_logger()

POLL_INTERVAL_S = 60


def _next_run_after(now: datetime, schedule: str) -> datetime:
    """Дублирует portal_api.services.cron_schedule.next_run_after.

    Зачем дубль: worker не зависит от portal-api пакета. Изменишь одно — не
    забудь второе. Тесты на оба контракта одинаковые.
    """
    if schedule == "hourly":
        return now + timedelta(hours=1)
    if schedule == "daily":
        return now + timedelta(days=1)
    if schedule == "weekly":
        return now + timedelta(days=7)
    if schedule == "monthly":
        # Аппроксимация без dateutil чтобы не тянуть в worker лишние deps.
        # 30 дней — простая и достаточная для cron'а.
        return now + timedelta(days=30)
    raise ValueError(f"unknown schedule preset: {schedule!r}")


def _due_cron_jobs(session: Session, now: datetime) -> list[dict]:
    """SELECT FOR UPDATE SKIP LOCKED — для безопасной обработки в multi-worker."""
    rows = session.execute(text("""
        SELECT cj.id, cj.agent_id, cj.params_jsonb, cj.schedule,
               cj.created_by_user_id, a.slug AS agent_slug
        FROM cron_jobs cj
        JOIN agents a ON a.id = cj.agent_id
        WHERE cj.enabled = true
          AND cj.next_run_at <= :now
        ORDER BY cj.next_run_at
        FOR UPDATE OF cj SKIP LOCKED
    """), {"now": now}).mappings().all()
    return [dict(r) for r in rows]


def _enqueue_one(
    session: Session,
    queue: Queue,
    row: dict,
    file_store_root_unused: object,
) -> None:
    """Создаёт Job в БД + кладёт в RQ. После — обновляет cron.next_run_at."""
    now = datetime.now(timezone.utc)
    new_job_id = uuid.uuid4()
    # INSERT job (status=queued). Минимум полей — runner подставит остальное.
    session.execute(text("""
        INSERT INTO jobs (id, agent_version_id, params_jsonb, status,
                          created_by_user_id, created_at)
        SELECT :jid, a.current_version_id, :p::jsonb, 'queued', :uid, :now
        FROM agents a WHERE a.id = :aid AND a.current_version_id IS NOT NULL
    """), {
        "jid": new_job_id, "p": _to_pg_json(row["params_jsonb"]),
        "uid": row["created_by_user_id"], "aid": row["agent_id"], "now": now,
    })
    # Если у агента нет current_version — INSERT не сработал; пропускаем.
    has_row = session.execute(
        text("SELECT 1 FROM jobs WHERE id = :jid"), {"jid": new_job_id},
    ).first()
    if not has_row:
        log.warning(
            "cron_skip_no_current_version", cron_id=str(row["id"]),
            agent_slug=row["agent_slug"],
        )
        # Двигаем next_run чтобы не зацикливаться.
        session.execute(text("""
            UPDATE cron_jobs SET next_run_at = :next, last_run_at = :now
            WHERE id = :cid
        """), {"next": _next_run_after(now, row["schedule"]), "now": now, "cid": row["id"]})
        return

    # Кладём в RQ
    queue.enqueue(
        "portal_worker.tasks.run_job.run_job",
        kwargs={"vid": str(new_job_id), "params": row["params_jsonb"]},
        job_timeout=1800,
    )

    # Двигаем расписание.
    session.execute(text("""
        UPDATE cron_jobs SET
            last_run_at = :now,
            next_run_at = :next,
            last_job_id = :jid
        WHERE id = :cid
    """), {
        "now": now, "next": _next_run_after(now, row["schedule"]),
        "jid": new_job_id, "cid": row["id"],
    })

    log.info(
        "cron_enqueued",
        cron_id=str(row["id"]),
        agent_slug=row["agent_slug"],
        job_id=str(new_job_id),
    )


def _to_pg_json(d: object) -> str:
    import json as _json
    return _json.dumps(d, default=str)


def _tick(database_url: str, redis_conn) -> None:
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            now = datetime.now(timezone.utc)
            due = _due_cron_jobs(session, now)
            if not due:
                session.commit()
                return
            queue = Queue("jobs", connection=redis_conn)
            for row in due:
                try:
                    _enqueue_one(session, queue, row, None)
                except Exception as e:  # noqa: BLE001
                    log.error("cron_enqueue_failed", cron_id=str(row["id"]), exc_info=e)
            session.commit()
    finally:
        engine.dispose()


def start_scheduler_thread(database_url: str, redis_conn) -> threading.Thread:
    """Запускает daemon-thread с polling-loop'ом."""
    def _loop():
        log.info("cron_scheduler_started", poll_interval_s=POLL_INTERVAL_S)
        while True:
            try:
                _tick(database_url, redis_conn)
            except Exception as e:  # noqa: BLE001
                log.error("cron_tick_failed", exc_info=e)
            time.sleep(POLL_INTERVAL_S)

    t = threading.Thread(target=_loop, name="cron-scheduler", daemon=True)
    t.start()
    return t
