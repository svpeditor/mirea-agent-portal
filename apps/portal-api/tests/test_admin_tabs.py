"""Тесты admin endpoints CRUD для вкладок."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Agent, AgentVersion, Tab, User
from tests.factories import make_agent, make_tab


async def _clear_tabs(db: AsyncSession) -> None:
    """Удалить все pre-bootstrap вкладки + агентов, чтобы тест работал в изоляции."""
    await db.execute(delete(AgentVersion))
    await db.execute(delete(Agent))
    await db.execute(delete(Tab))
    await db.flush()


@pytest.mark.asyncio
async def test_admin_lists_all_tabs_including_system(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)

    await make_tab(db, slug="научная-работа", name="Научная", order_idx=10)
    await make_tab(
        db, slug="uncategorized", name="Без категории", order_idx=999, is_system=True
    )
    await db.flush()

    resp = await admin_client.get("/api/admin/tabs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = [t["slug"] for t in body]
    # admin видит system tab даже без агентов
    assert "uncategorized" in slugs
    assert "научная-работа" in slugs
    # is_system должно быть в выдаче
    uncat = next(t for t in body if t["slug"] == "uncategorized")
    assert uncat["is_system"] is True
    sci = next(t for t in body if t["slug"] == "научная-работа")
    assert sci["is_system"] is False


@pytest.mark.asyncio
async def test_admin_creates_tab(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)

    resp = await admin_client.post(
        "/api/admin/tabs",
        json={"slug": "extra", "name": "Доп", "order_idx": 50},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["slug"] == "extra"
    assert body["name"] == "Доп"
    assert body["order_idx"] == 50
    assert body["is_system"] is False

    res = await db.execute(select(Tab).where(Tab.slug == "extra"))
    tab = res.scalar_one()
    assert tab.is_system is False


@pytest.mark.asyncio
async def test_admin_create_duplicate_slug_409(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)
    await make_tab(db, slug="dup", name="Dup")
    await db.commit()

    resp = await admin_client.post(
        "/api/admin/tabs",
        json={"slug": "dup", "name": "Other"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "TAB_SLUG_TAKEN"


@pytest.mark.asyncio
async def test_admin_patch_tab_name(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="old-name", name="Old")
    await db.commit()

    resp = await admin_client.patch(
        f"/api/admin/tabs/{tab.id}",
        json={"name": "New Name"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "New Name"
    assert body["slug"] == "old-name"  # slug не меняется


@pytest.mark.asyncio
async def test_admin_delete_empty_tab(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="to-delete", name="ToDel")
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/tabs/{tab.id}")
    assert resp.status_code == 204, resp.text

    res = await db.execute(select(Tab).where(Tab.id == tab.id))
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_admin_delete_tab_with_agents_409(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="busy", name="Busy")
    await make_agent(
        db,
        slug="some-agent",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/tabs/{tab.id}")
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "TAB_NOT_EMPTY"

    # Вкладка не должна быть удалена
    res = await db.execute(select(Tab).where(Tab.id == tab.id))
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_admin_cannot_delete_system_tab(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(
        db, slug="uncategorized", name="Без категории", is_system=True
    )
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/tabs/{tab.id}")
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "TAB_IS_SYSTEM"


@pytest.mark.asyncio
async def test_non_admin_user_forbidden(
    user_client: AsyncClient,
) -> None:
    resp = await user_client.get("/api/admin/tabs")
    assert resp.status_code == 403
