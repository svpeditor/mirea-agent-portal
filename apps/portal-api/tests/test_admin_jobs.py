"""GET /api/admin/jobs — admin видит все jobs всех юзеров."""
# ruff: noqa: RUF001, RUF002
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import User
from tests.factories import make_agent, make_agent_version, make_job, make_tab


async def _ready_agent(db: AsyncSession, admin_user: User, slug: str):
    tab = await make_tab(db, slug=f"aj-{slug}", name="T", order_idx=1)
    agent = await make_agent(
        db, slug=slug, tab_id=tab.id,
        created_by_user_id=admin_user.id, enabled=True,
    )
    version = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
    )
    agent.current_version_id = version.id
    await db.commit()
    return version


@pytest.mark.asyncio
async def test_admin_sees_all_jobs(
    admin_client: AsyncClient,
    db: AsyncSession,
    admin_user: User,
    regular_user: User,
) -> None:
    version = await _ready_agent(db, admin_user, slug="aj1")
    await make_job(db, agent_version_id=version.id, user_id=admin_user.id, status="ready")
    await make_job(db, agent_version_id=version.id, user_id=regular_user.id, status="ready")
    await db.commit()

    resp = await admin_client.get("/api/admin/jobs?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 2


@pytest.mark.asyncio
async def test_regular_user_403_on_admin_jobs(user_client: AsyncClient) -> None:
    resp = await user_client.get("/api/admin/jobs")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_jobs_invalid_limit(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/admin/jobs?limit=999")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_jobs_enriched_with_agent_brief(
    admin_client: AsyncClient,
    db: AsyncSession,
    admin_user: User,
) -> None:
    version = await _ready_agent(db, admin_user, slug="aj-enrich")
    await make_job(db, agent_version_id=version.id, user_id=admin_user.id, status="ready")
    await db.commit()

    resp = await admin_client.get("/api/admin/jobs?limit=20")
    body = resp.json()
    target = next((j for j in body if j["agent_slug"] == "aj-enrich"), None)
    assert target is not None
    assert "agent_name" in target
    assert "cost_usd_total" in target
