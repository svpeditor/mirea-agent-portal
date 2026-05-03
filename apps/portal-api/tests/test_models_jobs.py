"""ORM Job/JobEvent/JobFile + Pydantic DTO."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from portal_api.models import Job, JobEvent, JobFile
from portal_api.schemas.job import (
    JobCancelOut,
    JobCreatedOut,
    JobDetailOut,
    JobEventOut,
    JobListItemOut,
)
from tests.factories import make_agent, make_agent_version, make_tab


@pytest.mark.asyncio
async def test_create_job_minimal(db, admin_user) -> None:
    tab = await make_tab(db, slug="jobs-t1", name="T", order_idx=1)
    agent = await make_agent(db, slug="a", tab_id=tab.id, created_by_user_id=admin_user.id)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id)
    job = Job(
        id=uuid.uuid4(),
        agent_version_id=version.id,
        created_by_user_id=admin_user.id,
        status="queued",
        params_jsonb={"foo": "bar"},
    )
    db.add(job)
    await db.commit()

    fetched = (await db.execute(select(Job).where(Job.id == job.id))).scalar_one()
    assert fetched.status == "queued"
    assert fetched.params_jsonb == {"foo": "bar"}
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_job_event_seq_unique(db, admin_user) -> None:
    from sqlalchemy.exc import IntegrityError

    tab = await make_tab(db, slug="jobs-t2", name="T", order_idx=1)
    agent = await make_agent(db, slug="a2", tab_id=tab.id, created_by_user_id=admin_user.id)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id)
    job = Job(
        id=uuid.uuid4(), agent_version_id=version.id,
        created_by_user_id=admin_user.id, status="running", params_jsonb={},
    )
    db.add(job)
    await db.flush()

    db.add(JobEvent(id=uuid.uuid4(), job_id=job.id, seq=1,
                    event_type="started", payload_jsonb={"type": "started"}))
    await db.commit()

    db.add(JobEvent(id=uuid.uuid4(), job_id=job.id, seq=1,
                    event_type="progress", payload_jsonb={"type": "progress"}))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.asyncio
async def test_job_file_kind_unique(db, admin_user) -> None:
    from sqlalchemy.exc import IntegrityError

    tab = await make_tab(db, slug="jobs-t3", name="T", order_idx=1)
    agent = await make_agent(db, slug="a3", tab_id=tab.id, created_by_user_id=admin_user.id)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id)
    job = Job(
        id=uuid.uuid4(), agent_version_id=version.id,
        created_by_user_id=admin_user.id, status="queued", params_jsonb={},
    )
    db.add(job)
    await db.flush()

    db.add(JobFile(id=uuid.uuid4(), job_id=job.id, kind="input",
                   filename="a.txt", size_bytes=10, sha256="x", storage_key="k1"))
    await db.commit()

    db.add(JobFile(id=uuid.uuid4(), job_id=job.id, kind="input",
                   filename="a.txt", size_bytes=11, sha256="y", storage_key="k2"))
    with pytest.raises(IntegrityError):
        await db.commit()


def test_pydantic_dtos_have_expected_fields() -> None:
    assert "id" in JobCreatedOut.model_fields
    assert "status" in JobCreatedOut.model_fields
    assert "agent_slug" in JobCreatedOut.model_fields
    assert "events_count" in JobDetailOut.model_fields
    assert "last_event_seq" in JobDetailOut.model_fields
    assert "seq" in JobEventOut.model_fields
    assert "ts" in JobEventOut.model_fields
    assert "payload" in JobEventOut.model_fields
    assert "id" in JobListItemOut.model_fields
    assert "id" in JobCancelOut.model_fields
