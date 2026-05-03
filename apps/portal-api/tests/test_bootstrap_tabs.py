"""Бутстрап системных вкладок при пустой таблице tabs."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.bootstrap import bootstrap_tabs
from portal_api.models import Tab


@pytest.mark.asyncio
async def test_bootstrap_creates_four_tabs_when_empty(db: AsyncSession) -> None:
    await bootstrap_tabs(db)

    res = await db.execute(select(Tab).order_by(Tab.order_idx))
    tabs = res.scalars().all()

    assert len(tabs) == 4
    slugs = [t.slug for t in tabs]
    assert slugs == ["научная-работа", "учебная", "организационная", "uncategorized"]

    is_system_map = {t.slug: t.is_system for t in tabs}
    assert is_system_map == {
        "научная-работа": False,
        "учебная": False,
        "организационная": False,
        "uncategorized": True,
    }


@pytest.mark.asyncio
async def test_bootstrap_idempotent_when_tabs_exist(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    db.add(
        Tab(
            id=uuid.uuid4(),
            slug="custom-tab",
            name="Custom",
            icon="⭐",
            order_idx=5,
            is_system=False,
            created_at=now,
            updated_at=now,
        )
    )
    await db.flush()

    await bootstrap_tabs(db)

    res = await db.execute(select(Tab))
    tabs = res.scalars().all()
    assert len(tabs) == 1
    assert tabs[0].slug == "custom-tab"


@pytest.mark.asyncio
async def test_bootstrap_uncategorized_is_system(db: AsyncSession) -> None:
    await bootstrap_tabs(db)

    res = await db.execute(select(Tab).where(Tab.slug == "uncategorized"))
    uncat = res.scalar_one()
    assert uncat.is_system is True
    assert uncat.order_idx == 999
