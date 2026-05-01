"""Тесты GET /api/agents и GET /api/agents/{slug}."""
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
async def test_list_only_enabled_with_current_version(
    db: AsyncSession,
    user_client: AsyncClient,
    admin_user: User,
) -> None:
    """Только агенты с enabled=True И current_version_id IS NOT NULL попадают в список."""
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t-list", name="List Tab", order_idx=1)

    # 1. Disabled agent — не должен попасть
    await make_agent(
        db, slug="disabled-ag", tab_id=tab.id, created_by_user_id=admin_user.id, enabled=False
    )

    # 2. Enabled agent without current version — не должен попасть
    await make_agent(
        db, slug="no-version-ag", tab_id=tab.id, created_by_user_id=admin_user.id, enabled=True
    )

    # 3. Enabled agent with current version — должен попасть
    agent = await make_agent(
        db, slug="visible-ag", tab_id=tab.id, created_by_user_id=admin_user.id, enabled=False
    )
    version = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id)
    agent.current_version_id = version.id
    agent.enabled = True
    await db.commit()

    resp = await user_client.get("/api/agents")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = [a["slug"] for a in body]
    assert slugs == ["visible-ag"]


@pytest.mark.asyncio
async def test_list_does_not_leak_manifest_jsonb(
    db: AsyncSession,
    user_client: AsyncClient,
    admin_user: User,
) -> None:
    """GET /api/agents не должен возвращать поля manifest_jsonb."""
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t-leak", name="Leak Tab", order_idx=1)

    agent = await make_agent(
        db, slug="leak-ag", tab_id=tab.id, created_by_user_id=admin_user.id, enabled=False
    )
    version = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        manifest_jsonb={
            "id": "leak-test",
            "name": "T",
            "version": "0.1.0",
            "secret_field": "should-not-leak",
        },
    )
    agent.current_version_id = version.id
    agent.enabled = True
    await db.commit()

    resp = await user_client.get("/api/agents")
    assert resp.status_code == 200, resp.text
    assert "secret_field" not in resp.text


@pytest.mark.asyncio
async def test_get_by_slug_includes_full_manifest(
    db: AsyncSession,
    user_client: AsyncClient,
    admin_user: User,
) -> None:
    """GET /api/agents/{slug} возвращает полный manifest."""
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t-detail", name="Detail Tab", order_idx=1)

    agent = await make_agent(
        db, slug="detail-ag", tab_id=tab.id, created_by_user_id=admin_user.id, enabled=False
    )
    version = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        manifest_jsonb={"id": "agent-test", "name": "T", "version": "0.1.0"},
    )
    agent.current_version_id = version.id
    agent.enabled = True
    await db.commit()

    resp = await user_client.get("/api/agents/detail-ag")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == "detail-ag"
    assert body["manifest"]["id"] == "agent-test"


@pytest.mark.asyncio
async def test_get_by_slug_404_on_disabled(
    db: AsyncSession,
    user_client: AsyncClient,
    admin_user: User,
) -> None:
    """GET /api/agents/{slug} возвращает 404 для disabled агента."""
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t-disabled", name="Disabled Tab", order_idx=1)

    agent = await make_agent(
        db, slug="disabled-detail", tab_id=tab.id, created_by_user_id=admin_user.id, enabled=False
    )
    version = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id)
    agent.current_version_id = version.id
    # Оставляем enabled=False
    await db.commit()

    resp = await user_client.get("/api/agents/disabled-detail")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_list_sorted_by_name(
    db: AsyncSession,
    user_client: AsyncClient,
    admin_user: User,
) -> None:
    """GET /api/agents возвращает агентов отсортированных по имени."""
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t-sort", name="Sort Tab", order_idx=1)

    for slug, name in [("ag-z", "Z Agent"), ("ag-a", "A Agent"), ("ag-m", "M Agent")]:
        agent = await make_agent(
            db, slug=slug, name=name, tab_id=tab.id, created_by_user_id=admin_user.id, enabled=False
        )
        version = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id)
        agent.current_version_id = version.id
        agent.enabled = True

    await db.commit()

    resp = await user_client.get("/api/agents")
    assert resp.status_code == 200, resp.text
    names = [a["name"] for a in resp.json()]
    assert names == sorted(names)
    assert names == ["A Agent", "M Agent", "Z Agent"]


@pytest.mark.asyncio
async def test_unauthenticated_gets_401(client: AsyncClient) -> None:
    resp = await client.get("/api/agents")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "NOT_AUTHENTICATED"
