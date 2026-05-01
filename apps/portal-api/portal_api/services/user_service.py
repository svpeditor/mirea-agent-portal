# ruff: noqa: RUF002
"""Бизнес-логика юзеров: change-password, list, reset-password, ..."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import InvalidCredentials, UserNotFound
from portal_api.core.security import (
    hash_password,
    hash_refresh_token,
    verify_password,
)
from portal_api.models import RefreshToken, User


async def update_display_name(db: AsyncSession, user: User, new_name: str) -> User:
    user.display_name = new_name
    await db.flush()
    return user


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    *,
    keep_refresh_raw: str | None,
) -> None:
    """Меняет пароль. Отзывает все refresh кроме `keep_refresh_raw`.

    keep_refresh_raw — сырой refresh-токен из текущей cookie. Если передан и
    соответствует живому токену — НЕ отзываем его (текущая сессия остаётся).
    """
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentials()

    user.password_hash = hash_password(new_password)
    await db.flush()

    keep_hash = hash_refresh_token(keep_refresh_raw) if keep_refresh_raw else None
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    if keep_hash is not None:
        stmt = stmt.where(RefreshToken.token_hash != keep_hash)
    await db.execute(stmt)


async def list_users(
    db: AsyncSession,
    *,
    limit: int = 50,
    cursor: uuid.UUID | None = None,
) -> list[User]:
    stmt = select(User).order_by(User.created_at, User.id).limit(limit)
    if cursor is not None:
        cursor_user = await db.get(User, cursor)
        if cursor_user is not None:
            stmt = stmt.where(
                or_(
                    User.created_at > cursor_user.created_at,
                    and_(
                        User.created_at == cursor_user.created_at,
                        User.id > cursor_user.id,
                    ),
                )
            )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise UserNotFound()
    return user


async def update_user_admin(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    display_name: str | None,
    role: str | None,
    monthly_budget_usd: object | None,
) -> User:
    user = await get_user(db, user_id)
    if display_name is not None:
        user.display_name = display_name
    if role is not None:
        user.role = role
    if monthly_budget_usd is not None:
        user.monthly_budget_usd = monthly_budget_usd  # type: ignore[assignment]
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    user = await get_user(db, user_id)
    await db.delete(user)
    await db.flush()


async def reset_password(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Сгенерить новый временный пароль, revoke все refresh. Возвращает сырой пароль."""
    user = await get_user(db, user_id)
    new_password = secrets.token_urlsafe(12)
    user.password_hash = hash_password(new_password)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.flush()
    return new_password
