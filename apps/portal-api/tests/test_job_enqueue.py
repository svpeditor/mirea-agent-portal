"""JobEnqueuer публикует задачу в RQ-очередь jobs."""
from __future__ import annotations

import uuid

from redis import Redis
from rq import Queue

from portal_api.services.job_enqueue import JobEnqueuer


def test_enqueue_pushes_to_jobs_queue(redis_url: str, reset_redis) -> None:
    redis_conn = Redis.from_url(redis_url)
    enqueuer = JobEnqueuer(redis_url=redis_url, queue_name="jobs")
    job_id = uuid.uuid4()
    enqueuer.enqueue_run(job_id, timeout_seconds=120)

    q = Queue("jobs", connection=redis_conn)
    assert q.count == 1
    job = q.jobs[0]
    assert job.func_name == "portal_worker.tasks.run_job.run_job"
    # RQ 2.x payload — args=[{"job_id": ..., ephemeral_token?}]. См. comment в
    # services/job_enqueue.py:enqueue_run.
    assert job.args == [{"job_id": str(job_id)}]
    assert job.timeout == 120
