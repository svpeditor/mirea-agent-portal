# ruff: noqa: RUF003
"""Бизнес-логика auth: register / login / refresh / logout."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import get_settings
from portal_api.core.exceptions import (
    EmailAlreadyExists,
    InviteInvalid,
)
from portal_api.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
)
from portal_api.models import RefreshToken, User
from portal_api.schemas.auth import RegisterIn
from portal_api.services.invite_service import consume_invite, find_active_invite_by_token


async def register(
    db: AsyncSession,
    payload: RegisterIn,
    *,
    user_agent: str | None,
    ip: str | None,
) -> tuple[User, str, str]:
    """Регистрирует нового юзера по invite-токену.

    Возвращает (user, access_token, raw_refresh_token).
    """
    # 1) Валидируем invite
    invite = await find_active_invite_by_token(db, payload.token)

    # 2) email из payload должен совпасть с invite.email (case-insensitive)
    if invite.email.lower() != payload.email.lower():
        raise InviteInvalid()

    # 3) Этот email ещё не зарегистрирован?
    res = await db.execute(select(User).where(User.email == payload.email.lower()))
    if res.scalar_one_or_none() is not None:
        raise EmailAlreadyExists()

    # 4) Создаём юзера
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role="user",
    )
    db.add(user)
    await db.flush()

    # 5) Помечаем invite использованным (атомарно — защищает от race)
    await consume_invite(db, invite, used_by=user)

    # 6) Создаём пару access + refresh
    access = create_access_token(user_id=str(user.id), role=user.role)
    raw, raw_hash = generate_refresh_token()
    settings = get_settings()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=raw_hash,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        user_agent=user_agent,
        ip=ip,
    )
    db.add(rt)
    await db.flush()

    return user, access, raw
