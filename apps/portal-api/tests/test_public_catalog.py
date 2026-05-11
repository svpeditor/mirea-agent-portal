"""Тесты GET /api/public/catalog — без auth, landing-страница."""
# ruff: noqa: RUF001, RUF002
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Agent, AgentVersion, Tab, User
from tests.factories import make_agent, make_agent_version, make_tab


async def _clear(db: AsyncSession) -> None:
    await db.execute(delete(AgentVersion))
    await db.execute(delete(Agent))
    await db.execute(delete(Tab))
    await db.flush()


@pytest.fixture
async def anon_client(db: AsyncSession):  # type: ignore[no-untyped-def]
    """Клиент без cookies — анонимный."""
    from portal_api.deps import get_db
    from portal_api.main import app

    async def override_get_db():  # type: ignore[no-untyped-def]
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_public_catalog_no_auth(anon_client: AsyncClient) -> None:
    """Endpoint открыт всем — даже без cookies возвращает 200."""
    resp = await anon_client.get("/api/public/catalog")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "agents" in body
    assert "total_agents" in body


@pytest.mark.asyncio
async def test_public_catalog_returns_only_enabled(
    db: AsyncSession, anon_client: AsyncClient, admin_user: User,
) -> None:
    await _clear(db)
    tab = await make_tab(db, slug="pc-tab", name="Каталог", order_idx=1)

    # включённый агент с current_version
    a1 = await make_agent(
        db, slug="pc-enabled", name="Включён", tab_id=tab.id,
        created_by_user_id=admin_user.id, enabled=True,
    )
    v1 = await make_agent_version(
        db, agent_id=a1.id, created_by_user_id=admin_user.id, status="ready",
    )
    a1.current_version_id = v1.id

    # отключённый агент с current_version — НЕ должен попасть
    a2 = await make_agent(
        db, slug="pc-disabled", name="Выключен", tab_id=tab.id,
        created_by_user_id=admin_user.id, enabled=False,
    )
    v2 = await make_agent_version(
        db, agent_id=a2.id, created_by_user_id=admin_user.id, status="ready",
    )
    a2.current_version_id = v2.id

    # включённый без current_version — тоже не должен попасть
    await make_agent(
        db, slug="pc-no-version", name="Без версии", tab_id=tab.id,
        created_by_user_id=admin_user.id, enabled=True,
    )
    await db.commit()

    resp = await anon_client.get("/api/public/catalog")
    assert resp.status_code == 200
    body = resp.json()
    slugs = {a["slug"] for a in body["agents"]}
    assert slugs == {"pc-enabled"}
    assert body["total_agents"] == 1


@pytest.mark.asyncio
async def test_public_catalog_respects_limit(
    db: AsyncSession, anon_client: AsyncClient, admin_user: User,
) -> None:
    await _clear(db)
    tab = await make_tab(db, slug="pc-l", name="Tab", order_idx=1)
    for i in range(5):
        a = await make_agent(
            db, slug=f"pc-l-{i}", name=f"Agent {i}", tab_id=tab.id,
            created_by_user_id=admin_user.id, enabled=True,
        )
        v = await make_agent_version(
            db, agent_id=a.id, created_by_user_id=admin_user.id, status="ready",
        )
        a.current_version_id = v.id
    await db.commit()

    resp = await anon_client.get("/api/public/catalog?limit=2")
    body = resp.json()
    assert len(body["agents"]) == 2
    assert body["total_agents"] == 5  # total всё равно 5
