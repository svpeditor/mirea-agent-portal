"""Бутстрап первого админа при пустой БД."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings
from portal_api.core.security import hash_password
from portal_api.models import User


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
