"""Точка входа RQ worker."""
from __future__ import annotations

import redis
from rq import Worker

from portal_worker.config import get_settings
from portal_worker.core.logging import configure_logging
from portal_worker.tasks.build_agent import recover_orphaned_builds


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    recover_orphaned_builds()

    conn = redis.from_url(str(settings.redis_url))  # type: ignore[no-untyped-call]
    worker = Worker(queues=["builds"], connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
