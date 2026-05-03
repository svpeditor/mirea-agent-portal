"""Бутстрап первого админа при пустой БД."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings
from portal_api.core.security import hash_password
from portal_api.models import Tab, User


async def bootstrap_admin(db: AsyncSession, settings: Settings) -> None:
    """Создаёт первого админа, если БД пуста.

    - Если юзеров > 0 — ничего не делает.
    - Если юзеров 0 и ENV заданы — создаёт.
    - Если юзеров 0 и ENV пусты — RuntimeError (нельзя стартовать API).
    """
    res = await db.execute(select(User).limit(1))
    if res.scalar_one_or_none() is not None:
        return

    if not settings.initial_admin_email or not settings.initial_admin_password:
        raise RuntimeError(
            "Пустая БД, но INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD не заданы. "
            "Заполни .env и перезапусти API."
        )

    admin = User(
        email=str(settings.initial_admin_email).lower(),
        password_hash=hash_password(settings.initial_admin_password.get_secret_value()),
        display_name="Admin",
        role="admin",
    )
    db.add(admin)
    await db.commit()


_DEFAULT_TABS: list[dict[str, Any]] = [
    {
        "slug": "научная-работа",
        "name": "Научная работа",
        "icon": "🔬",
        "order_idx": 10,
        "is_system": False,
    },
    {
        "slug": "учебная",
        "name": "Учебная",
        "icon": "📘",
        "order_idx": 20,
        "is_system": False,
    },
    {
        "slug": "организационная",
        "name": "Организационная",
        "icon": "🗂",
        "order_idx": 30,
        "is_system": False,
    },
    {
        "slug": "uncategorized",
        "name": "Без категории",
        "icon": "❓",
        "order_idx": 999,
        "is_system": True,
    },
]


async def bootstrap_tabs(session: AsyncSession) -> None:
    """Если таблица tabs пуста — создать 4 системные вкладки."""
    existing = (await session.execute(select(Tab.id).limit(1))).first()
    if existing is not None:
        return
    now = datetime.now(UTC)
    for spec in _DEFAULT_TABS:
        session.add(Tab(**spec, created_at=now, updated_at=now))
    await session.commit()
