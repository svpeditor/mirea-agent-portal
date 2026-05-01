# ruff: noqa: RUF002
"""Тонкий wrapper над rq.Queue.enqueue, чтобы тесты могли его подменять."""
from __future__ import annotations

import uuid

from redis import Redis
from rq import Queue

_BUILD_QUEUE_NAME = "builds"
_BUILD_TASK = "portal_worker.tasks.build_agent.build_agent_version"
_BUILD_TIMEOUT = "15m"


class BuildEnqueuer:
    """Создаётся per-request через DI, чтобы тесты могли передать свой Redis."""

    def __init__(self, redis_url: str) -> None:
        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(_BUILD_QUEUE_NAME, connection=self._redis)

    def enqueue_build(self, version_id: uuid.UUID) -> None:
        self._queue.enqueue(
            _BUILD_TASK,
            str(version_id),
            job_timeout=_BUILD_TIMEOUT,
        )

    def close(self) -> None:
        self._redis.close()
