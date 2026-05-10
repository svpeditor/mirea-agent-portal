"""GET /api/jobs + GET /api/jobs/{id}."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.factories import make_agent, make_agent_version, make_tab


async def _ready_agent(db, admin_user, slug):
    tab = await make_tab(db, slug=f"ld-{slug}", name="T", order_idx=1)
    agent = await make_agent(db, slug=slug, tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    v = await make_agent_version(db, agent_id=agent.id,
                                  created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = v.id
    await db.commit()


def _mock_enqueuer():
    m = MagicMock()
    m.enqueue_run = MagicMock()
    return m


async def _create_job(client, slug):
    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer
    try:
        return await client.post(
            f"/api/agents/{slug}/jobs", data={"params": "{}"},
        )
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)


async def _login(client, user):
    resp = await client.post(
        "/api/auth/login", json={"email": user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_returns_only_own_jobs(
    user_client, admin_client, db, admin_user, regular_user,
) -> None:
    # user_client and admin_client share the same underlying client object.
    # Explicitly re-login to control which user is active for each action.
    await _ready_agent(db, admin_user, slug="own-list")

    # Create job as regular user
    await _login(user_client, regular_user)
    await _create_job(user_client, "own-list")

    # Create job as admin
    await _login(user_client, admin_user)
    await _create_job(user_client, "own-list")

    # Query as regular user — should only see own job
    await _login(user_client, regular_user)
    resp = await user_client.get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1


@pytest.mark.asyncio
async def test_list_pagination_cursor(user_client, db, admin_user) -> None:
    await _ready_agent(db, admin_user, slug="page")
    ids = []
    for _ in range(5):
        r = await _create_job(user_client, "page")
        ids.append(r.json()["job"]["id"])
    p1 = (await user_client.get("/api/jobs?limit=2")).json()
    assert len(p1) == 2
    p2 = (await user_client.get(f"/api/jobs?limit=2&before={p1[-1]['id']}")).json()
    assert len(p2) >= 1
    assert all(p["id"] != p1[-1]["id"] for p in p2)


@pytest.mark.asyncio
async def test_list_includes_agent_brief_and_cost(
    user_client, db, admin_user, regular_user,
) -> None:
    """JobListItemOut должен содержать agent_slug/agent_name/cost_usd_total
    через join на agent_version → agent. Frontend JobsTable рендерит
    их вместо truncated UUID. cost_usd_total дефолтно "0" из БД."""
    tab = await make_tab(db, slug="ld-en", name="T", order_idx=1)
    agent = await make_agent(
        db, slug="enriched", name="Эталон Эхо", tab_id=tab.id,
        created_by_user_id=admin_user.id, enabled=True,
    )
    v = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
    )
    agent.current_version_id = v.id
    await db.commit()

    await _login(user_client, regular_user)
    await _create_job(user_client, "enriched")
    resp = await user_client.get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["agent_slug"] == "enriched"
    assert item["agent_name"] == "Эталон Эхо"
    # Numeric(10,6) сериализуется как строка через pydantic Decimal
    assert item["cost_usd_total"] == "0.000000"


@pytest.mark.asyncio
async def test_get_detail_owner(user_client, db, admin_user) -> None:
    await _ready_agent(db, admin_user, slug="det")
    r = await _create_job(user_client, "det")
    job_id = r.json()["job"]["id"]
    resp = await user_client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert body["agent"]["slug"] == "det"
    assert body["events_count"] == 0
    assert body["last_event_seq"] is None


@pytest.mark.asyncio
async def test_get_detail_404_for_other_user(
    user_client, admin_client, db, admin_user, regular_user,
) -> None:
    await _ready_agent(db, admin_user, slug="other")

    # Create job as admin
    await _login(user_client, admin_user)
    r = await _create_job(user_client, "other")
    job_id = r.json()["job"]["id"]

    # Query as regular user — should 404
    await _login(user_client, regular_user)
    resp = await user_client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 404
