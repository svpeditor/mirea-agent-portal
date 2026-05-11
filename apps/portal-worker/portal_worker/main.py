"""Точка входа RQ worker."""
from __future__ import annotations

from redis import Redis
from rq import Worker

from portal_worker.config import get_settings
from portal_worker.core.logging import configure_logging
from portal_worker.core.sentry import init_sentry
from portal_worker.services.cron_scheduler import start_scheduler_thread
from portal_worker.tasks.build_agent import recover_orphaned_builds
from portal_worker.tasks.run_job import recover_orphaned_jobs


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_sentry(settings)

    recover_orphaned_builds()
    recover_orphaned_jobs()

    conn = Redis.from_url(str(settings.redis_url))

    # Cron scheduler: daemon-thread, 60с tick.
    # Заодно если worker рестартанётся — thread поднимается заново.
    sync_url = _sync_db_url(str(settings.database_url))
    start_scheduler_thread(sync_url, conn)

    worker = Worker(["builds", "jobs"], connection=conn)
    worker.work(with_scheduler=False)


def _sync_db_url(async_url: str) -> str:
    """Нормализует URL для sync SQLAlchemy.

    `postgresql+asyncpg://` → `postgresql://` (для psycopg2 driver, который
    SA подберёт по дефолту). `postgresql+psycopg2://` оставляем как есть.
    """
    if "+asyncpg" in async_url:
        return async_url.replace("+asyncpg", "")
    return async_url


if __name__ == "__main__":
    main()
