"""GET /api/jobs/{id}/events?since=N."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from portal_api.models import JobEvent
from tests.factories import make_agent, make_agent_version, make_tab


def _mock_enqueuer():
    m = MagicMock()
    m.enqueue_run = MagicMock()
    return m


async def _login(client, user):
    resp = await client.post(
        "/api/auth/login", json={"email": user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_events_since_returns_only_new(
    user_client, db, admin_user,
) -> None:
    tab = await make_tab(db, slug="evs-tab", name="T", order_idx=1)
    agent = await make_agent(db, slug="evs-agent", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    v = await make_agent_version(db, agent_id=agent.id,
                                  created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = v.id
    await db.commit()

    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    app.dependency_overrides[get_job_enqueuer] = lambda: _mock_enqueuer()
    r = await user_client.post("/api/agents/evs-agent/jobs", data={"params": "{}"})
    app.dependency_overrides.pop(get_job_enqueuer, None)
    job_id = r.json()["job"]["id"]
    for s in (1, 2, 3, 4):
        db.add(JobEvent(
            id=uuid.uuid4(), job_id=uuid.UUID(job_id), seq=s,
            event_type="progress", payload_jsonb={"v": s},
        ))
    await db.commit()

    resp = await user_client.get(f"/api/jobs/{job_id}/events?since=2")
    assert resp.status_code == 200
    body = resp.json()
    assert [e["seq"] for e in body] == [3, 4]
    assert body[0]["payload"]["v"] == 3


@pytest.mark.asyncio
async def test_events_404_for_other_user(
    user_client, admin_client, db, admin_user, regular_user,
) -> None:
    tab = await make_tab(db, slug="evso-tab", name="T", order_idx=1)
    agent = await make_agent(db, slug="evso", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    v = await make_agent_version(db, agent_id=agent.id,
                                  created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = v.id
    await db.commit()

    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    # Create job as admin
    await _login(user_client, admin_user)
    app.dependency_overrides[get_job_enqueuer] = lambda: _mock_enqueuer()
    r = await user_client.post("/api/agents/evso/jobs", data={"params": "{}"})
    app.dependency_overrides.pop(get_job_enqueuer, None)
    job_id = r.json()["job"]["id"]

    # Query events as regular user — should 404
    await _login(user_client, regular_user)
    resp = await user_client.get(f"/api/jobs/{job_id}/events")
    assert resp.status_code == 404
