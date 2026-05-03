# ruff: noqa: RUF002
"""Бизнес-логика для вкладок."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import (
    TabIsSystemError,
    TabNotEmptyError,
    TabNotFoundError,
    TabSlugTakenError,
)
from portal_api.models import Agent, Tab


async def list_public_tabs(session: AsyncSession) -> list[Tab]:
    """Список вкладок для публичного UI.

    Системную вкладку `uncategorized` (is_system=True) скрываем, если в ней
    нет ни одного enabled-агента с current_version_id.
    Сортировка: order_idx, name.
    """
    has_enabled_agent = (
        select(Agent.id)
        .where(
            Agent.tab_id == Tab.id,
            Agent.enabled.is_(True),
            Agent.current_version_id.is_not(None),
        )
        .exists()
    )
    stmt = (
        select(Tab)
        .where((Tab.is_system.is_(False)) | has_enabled_agent)
        .order_by(Tab.order_idx, Tab.name)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_admin_tabs(session: AsyncSession) -> list[Tab]:
    """Список ВСЕХ вкладок для admin UI (включая системные, без uncategorized-hide)."""
    stmt = select(Tab).order_by(Tab.order_idx, Tab.name)
    return list((await session.execute(stmt)).scalars().all())


async def get_tab(session: AsyncSession, tab_id: uuid.UUID) -> Tab:
    """Найти вкладку по id или кинуть TabNotFoundError."""
    tab = await session.get(Tab, tab_id)
    if tab is None:
        raise TabNotFoundError()
    return tab


async def create_tab(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    icon: str | None = None,
    order_idx: int = 0,
) -> Tab:
    """Создать вкладку. На дубль slug кидает TabSlugTakenError."""
    tab = Tab(
        slug=slug,
        name=name,
        icon=icon,
        order_idx=order_idx,
        is_system=False,
    )
    session.add(tab)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise TabSlugTakenError() from e
    return tab


async def update_tab(
    session: AsyncSession,
    tab_id: uuid.UUID,
    *,
    name: str | None = None,
    icon: str | None = None,
    order_idx: int | None = None,
) -> Tab:
    """Изменить name/icon/order_idx у вкладки. Slug и is_system не меняем."""
    tab = await get_tab(session, tab_id)
    if name is not None:
        tab.name = name
    if icon is not None:
        tab.icon = icon
    if order_idx is not None:
        tab.order_idx = order_idx
    tab.updated_at = datetime.now(UTC)
    await session.flush()
    return tab


async def delete_tab(session: AsyncSession, tab_id: uuid.UUID) -> None:
    """Удалить вкладку.

    - Системную (`is_system=True`) удалять нельзя → TabIsSystemError (403).
    - Если в вкладке есть агенты → TabNotEmptyError (409).
    """
    tab = await get_tab(session, tab_id)
    if tab.is_system:
        raise TabIsSystemError()

    count_stmt = select(func.count()).select_from(Agent).where(Agent.tab_id == tab_id)
    count = (await session.execute(count_stmt)).scalar_one()
    if count > 0:
        raise TabNotEmptyError()

    await session.delete(tab)
    await session.flush()
