# ruff: noqa: RUF002, RUF003
"""Бизнес-логика auth: register / login / refresh / logout."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import get_settings
from portal_api.core.exceptions import (
    EmailAlreadyExists,
    InvalidCredentials,
    InviteInvalid,
    RefreshInvalid,
    RefreshReuseDetected,
)
from portal_api.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from portal_api.models import RefreshToken, User, UserQuota
from portal_api.schemas.auth import RegisterIn
from portal_api.services.invite_service import consume_invite, find_active_invite_by_token
from portal_api.services.llm_quota import _floor_to_month_start_msk_utc

_log = structlog.get_logger(__name__)

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

    # 4) Создаём юзера. Роль берём из инвайта - админ при выдаче приглашения
    # сам выбирает, в какой роли регистрировать гостя.
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=invite.role,
    )
    db.add(user)
    await db.flush()

    # 4b) Создаём UserQuota с дефолтными лимитами из настроек
    settings = get_settings()
    limit_usd = (
        Decimal("999999.9999") if user.role == "admin"
        else settings.llm_default_user_quota_usd
    )
    quota = UserQuota(
        user_id=user.id,
        monthly_limit_usd=limit_usd,
        per_job_cap_usd=settings.llm_default_per_job_cap_usd,
        period_starts_at=_floor_to_month_start_msk_utc(datetime.now(UTC)),
    )
    db.add(quota)
    await db.flush()

    # 5) Помечаем invite использованным (атомарно — защищает от race)
    await consume_invite(db, invite, used_by=user)

    # 6) Создаём пару access + refresh
    access = create_access_token(user_id=str(user.id), role=user.role)
    raw, raw_hash = generate_refresh_token()
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


async def refresh(
    db: AsyncSession,
    raw_refresh: str | None,
    *,
    user_agent: str | None,
    ip: str | None,
) -> tuple[User, str, str]:
    """Ротирует refresh-токен. Возвращает (user, new_access, new_raw_refresh).

    На reuse-attack — revoke все refresh юзера, кидает RefreshReuseDetected.
    """
    if not raw_refresh:
        raise RefreshInvalid()

    h = hash_refresh_token(raw_refresh)

    res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    token = res.scalar_one_or_none()
    if token is None:
        raise RefreshInvalid()

    # Reuse-attack: токен существует, но уже revoked
    if token.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == token.user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await db.commit()  # Persist the revoke-all BEFORE raising;
                           # otherwise get_db rolls it back on exception.
        _log.warning(
            "refresh_reuse_detected",
            user_id=str(token.user_id),
            old_user_agent=token.user_agent,
            old_ip=str(token.ip) if token.ip else None,
            new_user_agent=user_agent,
            new_ip=ip,
        )
        raise RefreshReuseDetected()

    if token.expires_at <= datetime.now(UTC):
        raise RefreshInvalid()

    # Ротация: создаём новый, помечаем старый
    res2 = await db.execute(select(User).where(User.id == token.user_id))
    user = res2.scalar_one()

    new_raw, new_hash = generate_refresh_token()
    settings = get_settings()
    new_token = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        user_agent=user_agent,
        ip=ip,
    )
    db.add(new_token)
    await db.flush()

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token.id)
        .values(revoked_at=datetime.now(UTC), replaced_by_id=new_token.id)
    )

    new_access = create_access_token(user_id=str(user.id), role=user.role)
    return user, new_access, new_raw
