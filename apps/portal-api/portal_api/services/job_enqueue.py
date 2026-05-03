"""RQ enqueuer для jobs."""
from __future__ import annotations

import uuid

from redis import Redis
from rq import Queue


class JobEnqueuer:
    """Публикует задачу run_job в RQ."""

    def __init__(self, *, redis_url: str, queue_name: str = "jobs") -> None:
        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(queue_name, connection=self._redis)

    def enqueue_run(self, job_id: uuid.UUID, *, timeout_seconds: int) -> None:
        self._queue.enqueue(
            "portal_worker.tasks.run_job.run_job",
            str(job_id),
            job_timeout=timeout_seconds,
        )
