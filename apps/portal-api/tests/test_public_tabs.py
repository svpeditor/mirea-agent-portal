"""Тесты публичного эндпоинта GET /api/tabs."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Agent, AgentVersion, Tab, User
from tests.factories import make_agent, make_agent_version, make_tab


async def _clear_tabs(db: AsyncSession) -> None:
    """Удалить все pre-bootstrap вкладки + агентов, чтобы тест работал в изоляции."""
    await db.execute(delete(AgentVersion))
    await db.execute(delete(Agent))
    await db.execute(delete(Tab))
    await db.flush()


@pytest.mark.asyncio
async def test_lists_tabs_sorted_by_order_idx(
    db: AsyncSession,
    user_client: AsyncClient,
) -> None:
    await _clear_tabs(db)

    # Вставляем в обратном порядке от ожидаемого
    await make_tab(db, slug="c-tab", name="C", order_idx=30)
    await make_tab(db, slug="b-tab", name="B", order_idx=20)
    await make_tab(db, slug="a-tab", name="A", order_idx=10)
    await db.flush()

    resp = await user_client.get("/api/tabs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = [t["slug"] for t in body]
    assert slugs == ["a-tab", "b-tab", "c-tab"]


@pytest.mark.asyncio
async def test_uncategorized_hidden_when_empty(
    db: AsyncSession,
    user_client: AsyncClient,
) -> None:
    await _clear_tabs(db)

    await make_tab(db, slug="научная-работа", name="Научная", order_idx=10)
    await make_tab(
        db, slug="uncategorized", name="Без категории", order_idx=999, is_system=True
    )
    await db.flush()

    resp = await user_client.get("/api/tabs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = [t["slug"] for t in body]
    assert "uncategorized" not in slugs
    assert slugs == ["научная-работа"]


@pytest.mark.asyncio
async def test_uncategorized_visible_when_has_enabled_agent(
    db: AsyncSession,
    user_client: AsyncClient,
    regular_user: User,
) -> None:
    await _clear_tabs(db)

    await make_tab(db, slug="научная-работа", name="Научная", order_idx=10)
    uncat = await make_tab(
        db, slug="uncategorized", name="Без категории", order_idx=999, is_system=True
    )
    agent = await make_agent(
        db,
        slug="orphan-agent",
        tab_id=uncat.id,
        created_by_user_id=regular_user.id,
        enabled=True,
    )
    version = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=regular_user.id,
    )
    agent.current_version_id = version.id
    await db.flush()

    resp = await user_client.get("/api/tabs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = [t["slug"] for t in body]
    assert "uncategorized" in slugs
    assert slugs == ["научная-работа", "uncategorized"]


@pytest.mark.asyncio
async def test_unauthenticated_gets_401(client: AsyncClient) -> None:
    resp = await client.get("/api/tabs")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "NOT_AUTHENTICATED"
