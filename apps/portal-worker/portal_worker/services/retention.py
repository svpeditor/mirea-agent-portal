"""Retention-чистка файлов завершённых job'ов.

Препод просил: найденный материал хранится ~N дней, потом авто-удаляется.
Daemon-thread (по образцу cron_scheduler) раз в час проходит по job'ам в
терминальном статусе старше retention_days и удаляет их файлы с диска +
строки job_files. Сам job и его события/summary остаются как история.

Идемпотентно: job без файлов на диске и без строк job_files пропускается,
так что повторный проход ничего не делает.
"""
from __future__ import annotations

import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

log = structlog.get_logger()

_TERMINAL = ("ready", "failed", "cancelled")


def purge_expired_job_files(
    database_url: str,
    file_store_root: Path,
    retention_days: int,
    now: datetime | None = None,
) -> list[str]:
    """Удалить файлы + job_files для терминальных job'ов старше retention_days.

    Возвращает список job_id, по которым что-то реально удалили.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    root = Path(file_store_root)
    purged: list[str] = []

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            rows = session.execute(text("""
                SELECT id FROM jobs
                WHERE status = ANY(:terminal)
                  AND finished_at IS NOT NULL
                  AND finished_at < :cutoff
                ORDER BY finished_at
            """), {"terminal": list(_TERMINAL), "cutoff": cutoff}).scalars().all()

            for jid in rows:
                job_dir = root / str(jid)
                has_dir = job_dir.exists()
                has_files = session.execute(
                    text("SELECT EXISTS(SELECT 1 FROM job_files WHERE job_id=:j)"),
                    {"j": jid},
                ).scalar_one()
                if not has_dir and not has_files:
                    continue  # уже чисто — идемпотентность

                if has_dir:
                    # job_dir = file_store_root/<uuid>; защита от кривого root
                    if not _safe_under(root, job_dir):
                        log.error("retention_unsafe_path", path=str(job_dir))
                        continue
                    errs: list[str] = []

                    def _onexc(_func, path, _exc, _e=errs) -> None:
                        _e.append(str(path))

                    shutil.rmtree(job_dir, onexc=_onexc)
                    if errs:
                        # частичное удаление: НЕ чистим job_files, чтобы БД и
                        # диск не разошлись молча — добьём на следующем тике.
                        log.error("retention_rmtree_partial",
                                  job_id=str(jid), failed=errs[:5])
                        continue
                if has_files:
                    session.execute(
                        text("DELETE FROM job_files WHERE job_id=:j"), {"j": jid}
                    )
                purged.append(str(jid))

            if purged:
                session.commit()
            else:
                session.rollback()
    finally:
        engine.dispose()

    if purged:
        log.info("retention_purged", count=len(purged), retention_days=retention_days)
    return purged


def _safe_under(root: Path, target: Path) -> bool:
    """target обязан быть прямым потомком root и именем-UUID (anti foot-gun)."""
    try:
        rel = target.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    if len(rel.parts) != 1:
        return False
    try:
        uuid.UUID(rel.parts[0])
    except ValueError:
        return False
    return True


def start_retention_thread(
    database_url: str,
    file_store_root: Path,
    retention_days: int,
    poll_interval_s: int,
) -> threading.Thread:
    """daemon-thread: раз в poll_interval_s чистит просроченные job-файлы."""
    def _loop() -> None:
        log.info(
            "retention_started",
            retention_days=retention_days,
            poll_interval_s=poll_interval_s,
        )
        while True:
            try:
                purge_expired_job_files(database_url, file_store_root, retention_days)
            except Exception as e:  # noqa: BLE001
                log.error("retention_tick_failed", exc_info=e)
            time.sleep(poll_interval_s)

    t = threading.Thread(target=_loop, name="retention", daemon=True)
    t.start()
    return t
