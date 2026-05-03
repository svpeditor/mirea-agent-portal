"""job_service: create_job + queries; job_event_service.list_since."""
from __future__ import annotations

import uuid

import pytest

from portal_api.core.exceptions import (
    AgentNotFoundError, AgentNotReadyError, JobNotFoundError,
)
from portal_api.models import Job, JobEvent
from portal_api.services import job_event_service, job_service
from tests.factories import make_agent, make_agent_version, make_tab


async def _enabled_agent_with_ready_version(db, admin_user, slug="echo"):
    tab = await make_tab(db, slug=f"tab-{slug}", name="T", order_idx=1)
    agent = await make_agent(db, slug=slug, tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id,
                                        status="ready")
    agent.current_version_id = version.id
    await db.commit()
    return agent, version


@pytest.mark.asyncio
async def test_create_job_happy_path(db, admin_user) -> None:
    agent, version = await _enabled_agent_with_ready_version(db, admin_user)
    job = await job_service.create_job(
        db, agent_slug=agent.slug, params={"x": 1}, user_id=admin_user.id,
    )
    assert job.status == "queued"
    assert job.agent_version_id == version.id
    assert job.params_jsonb == {"x": 1}


@pytest.mark.asyncio
async def test_create_job_unknown_slug_raises(db, admin_user) -> None:
    with pytest.raises(AgentNotFoundError):
        await job_service.create_job(
            db, agent_slug="no-such", params={}, user_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_create_job_disabled_agent_raises(db, admin_user) -> None:
    tab = await make_tab(db, slug="dis-t", name="T", order_idx=1)
    agent = await make_agent(db, slug="dis", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=False)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = version.id
    await db.commit()

    with pytest.raises(AgentNotFoundError):
        await job_service.create_job(
            db, agent_slug="dis", params={}, user_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_create_job_no_current_version_raises(db, admin_user) -> None:
    tab = await make_tab(db, slug="nov-t", name="T", order_idx=1)
    agent = await make_agent(db, slug="nov", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    await db.commit()

    with pytest.raises(AgentNotFoundError):
        await job_service.create_job(
            db, agent_slug="nov", params={}, user_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_create_job_version_not_ready_raises(db, admin_user) -> None:
    tab = await make_tab(db, slug="nr-t", name="T", order_idx=1)
    agent = await make_agent(db, slug="nr", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id,
                                        status="building")
    agent.current_version_id = version.id
    await db.commit()

    with pytest.raises(AgentNotReadyError):
        await job_service.create_job(
            db, agent_slug="nr", params={}, user_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_get_job_for_user_owner_sees(db, admin_user) -> None:
    agent, version = await _enabled_agent_with_ready_version(db, admin_user, slug="own1")
    job = await job_service.create_job(
        db, agent_slug=agent.slug, params={}, user_id=admin_user.id,
    )
    fetched = await job_service.get_job_for_user(db, job.id, admin_user)
    assert fetched is not None
    assert fetched.id == job.id


@pytest.mark.asyncio
async def test_get_job_for_user_other_user_returns_none(db, admin_user, regular_user) -> None:
    agent, _ = await _enabled_agent_with_ready_version(db, admin_user, slug="own2")
    job = await job_service.create_job(
        db, agent_slug=agent.slug, params={}, user_id=admin_user.id,
    )
    fetched = await job_service.get_job_for_user(db, job.id, regular_user)
    assert fetched is None


@pytest.mark.asyncio
async def test_list_for_user_pagination(db, admin_user) -> None:
    agent, _ = await _enabled_agent_with_ready_version(db, admin_user, slug="lst")
    ids = []
    for _ in range(5):
        j = await job_service.create_job(
            db, agent_slug=agent.slug, params={}, user_id=admin_user.id,
        )
        ids.append(j.id)
    page = await job_service.list_for_user(db, admin_user, limit=3, before=None)
    assert len(page) == 3
    page2 = await job_service.list_for_user(db, admin_user, limit=3, before=page[-1].id)
    assert len(page2) >= 1
    assert all(p.id != page[-1].id for p in page2)


@pytest.mark.asyncio
async def test_list_events_since_filters_by_seq(db, admin_user) -> None:
    agent, _ = await _enabled_agent_with_ready_version(db, admin_user, slug="evs")
    job = await job_service.create_job(
        db, agent_slug=agent.slug, params={}, user_id=admin_user.id,
    )
    for s in (1, 2, 3, 4, 5):
        db.add(JobEvent(
            id=uuid.uuid4(), job_id=job.id, seq=s,
            event_type="progress", payload_jsonb={"type": "progress", "value": s / 5},
        ))
    await db.commit()
    events = await job_event_service.list_since(db, job.id, since=2, limit=10)
    seqs = [e["seq"] for e in events]
    assert seqs == [3, 4, 5]
