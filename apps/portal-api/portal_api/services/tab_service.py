# ruff: noqa: RUF002
"""Бизнес-логика для вкладок."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
