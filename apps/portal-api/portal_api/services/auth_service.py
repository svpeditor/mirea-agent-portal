# ruff: noqa: RUF003
"""Бизнес-логика auth: register / login / refresh / logout."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import get_settings
from portal_api.core.exceptions import (
    EmailAlreadyExists,
    InvalidCredentials,
    InviteInvalid,
)
from portal_api.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from portal_api.models import RefreshToken, User
from portal_api.schemas.auth import RegisterIn
from portal_api.services.invite_service import consume_invite, find_active_invite_by_token

_DUMMY_PASSWORD_HASH: str | None = None


def _get_dummy_hash() -> str:
    """Precomputed bcrypt hash for timing-pad on login of nonexistent users."""
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-pad")
    return _DUMMY_PASSWORD_HASH


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


async def login(
    db: AsyncSession,
    email: str,
    password: str,
    *,
    user_agent: str | None,
    ip: str | None,
) -> tuple[User, str, str]:
    """Логин по email/password. Возвращает (user, access, raw_refresh)."""
    email = email.lower()
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        # Constant-time на отсутствующего юзера: всё равно сравним bcrypt с
        # валидным dummy-хешем — съест ~170ms, тот же порядок что и при настоящей проверке.
        if user is None:
            verify_password(password, _get_dummy_hash())
        raise InvalidCredentials()

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


async def logout(db: AsyncSession, raw_refresh: str | None) -> None:
    """Отзывает refresh-токен по сырому значению из cookie. Идемпотентно."""
    if not raw_refresh:
        return
    h = hash_refresh_token(raw_refresh)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == h, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
