"""BuildEnqueuer кладёт задачу в Redis-очередь."""
from __future__ import annotations

import uuid


async def test_enqueues_to_builds_queue(redis_url: str, reset_redis: None) -> None:
    from redis import Redis
    from rq import Queue

    from portal_api.services.build_enqueue import BuildEnqueuer

    eq = BuildEnqueuer(redis_url)
    vid = uuid.uuid4()
    eq.enqueue_build(vid)
    eq.close()

    q = Queue("builds", connection=Redis.from_url(redis_url))
    assert q.count == 1
    job = q.jobs[0]
    assert job.func_name == "portal_worker.tasks.build_agent.build_agent_version"
    assert job.args == (str(vid),)


async def test_two_enqueues_two_jobs(redis_url: str, reset_redis: None) -> None:
    from redis import Redis
    from rq import Queue

    from portal_api.services.build_enqueue import BuildEnqueuer

    eq = BuildEnqueuer(redis_url)
    eq.enqueue_build(uuid.uuid4())
    eq.enqueue_build(uuid.uuid4())
    eq.close()

    q = Queue("builds", connection=Redis.from_url(redis_url))
    assert q.count == 2
