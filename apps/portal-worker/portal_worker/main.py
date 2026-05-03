"""Точка входа RQ worker."""
from __future__ import annotations

from redis import Redis
from rq import Worker

from portal_worker.config import get_settings
from portal_worker.core.logging import configure_logging
from portal_worker.tasks.build_agent import recover_orphaned_builds
from portal_worker.tasks.run_job import recover_orphaned_jobs


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    recover_orphaned_builds()
    recover_orphaned_jobs()

    conn = Redis.from_url(str(settings.redis_url))
    worker = Worker(["builds", "jobs"], connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
