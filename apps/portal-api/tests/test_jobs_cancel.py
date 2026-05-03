"""POST /api/jobs/{id}/cancel."""
from __future__ import annotations

import copy
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from portal_api.models import Job
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


async def _ready_agent_with_job(client, db, admin_user, slug):
    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    tab = await make_tab(db, slug=f"cnc-{slug}", name="T", order_idx=1)
    agent = await make_agent(db, slug=slug, tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    v = await make_agent_version(db, agent_id=agent.id,
                                  created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = v.id
    await db.commit()
    app.dependency_overrides[get_job_enqueuer] = lambda: _mock_enqueuer()
    try:
        r = await client.post(f"/api/agents/{slug}/jobs", data={"params": "{}"})
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)
    return uuid.UUID(r.json()["job"]["id"])


def _make_settings_override_redis(redis_url):
    from portal_api.config import get_settings
    base = get_settings()
    s = copy.copy(base)
    object.__setattr__(s, "redis_url", redis_url)
    return lambda: s


@pytest.mark.asyncio
async def test_cancel_queued_job(user_client, db, admin_user, redis_url) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override_redis(redis_url)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="cnc-q")
        resp = await user_client.post(f"/api/jobs/{job_id}/cancel")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cancelled"
        assert body["id"] == str(job_id)

        # Verify DB
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one()
        assert job.status == "cancelled"
        assert job.finished_at is not None
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_cancel_queued_idempotent(user_client, db, admin_user, redis_url) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override_redis(redis_url)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="cnc-idem")
        r1 = await user_client.post(f"/api/jobs/{job_id}/cancel")
        assert r1.status_code == 200
        r2 = await user_client.post(f"/api/jobs/{job_id}/cancel")
        assert r2.status_code == 200
        assert r2.json()["status"] == "cancelled"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_cancel_already_finished_409(user_client, db, admin_user, redis_url) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override_redis(redis_url)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="cnc-fin")

        # Force job to "ready" (finished) status directly in DB
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one()
        job.status = "ready"
        await db.commit()

        resp = await user_client.post(f"/api/jobs/{job_id}/cancel")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "job_already_finished"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_cancel_404_for_other_user(
    user_client, admin_client, db, admin_user, regular_user, redis_url,
) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override_redis(redis_url)
    try:
        # Create job as admin
        await _login(user_client, admin_user)
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="cnc-other")

        # Try to cancel as regular user
        await _login(user_client, regular_user)
        resp = await user_client.post(f"/api/jobs/{job_id}/cancel")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_cancel_nonexistent_404(user_client, redis_url) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override_redis(redis_url)
    try:
        fake_id = uuid.uuid4()
        resp = await user_client.post(f"/api/jobs/{fake_id}/cancel")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)
