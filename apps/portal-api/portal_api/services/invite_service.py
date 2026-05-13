"""Бизнес-логика invite-токенов."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import (
    EmailAlreadyRegistered,
    InviteAlreadyPending,
    InviteInvalid,
)
from portal_api.models import Invite, User

INVITE_TTL_DAYS = 7


async def find_active_invite_by_token(db: AsyncSession, token: str) -> Invite:
    """Возвращает живой invite или кидает InviteInvalid.

    Атомарно проверяет: токен существует, used_at IS NULL, expires_at > now().
    """
    res = await db.execute(select(Invite).where(Invite.token == token))
    invite = res.scalar_one_or_none()
    if invite is None:
        raise InviteInvalid()
    if invite.used_at is not None:
        raise InviteInvalid()
    if invite.expires_at <= datetime.now(UTC):
        raise InviteInvalid()
    return invite


async def consume_invite(db: AsyncSession, invite: Invite, used_by: User | None) -> None:
    """Атомарно помечает invite использованным.

    Если кто-то уже использовал между find и consume — UPDATE вернёт 0 rows
    и кидаем InviteInvalid (это и есть защита от race condition).
    """
    used_by_id = used_by.id if used_by else None
    result = await db.execute(
        update(Invite)
        .where(Invite.id == invite.id, Invite.used_at.is_(None))
        .values(used_at=datetime.now(UTC), used_by_user_id=used_by_id)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise InviteInvalid()


async def create_invite(
    db: AsyncSession,
    *,
    email: str,
    created_by: User,
    role: str = "user",
) -> Invite:
    """Создать invite. Кидает EmailAlreadyRegistered / InviteAlreadyPending по правилам."""
    email = email.lower()
    if role not in ("user", "admin"):
        role = "user"

    # 1) email уже зарегистрирован?
    res = await db.execute(select(User).where(User.email == email))
    if res.scalar_one_or_none() is not None:
        raise EmailAlreadyRegistered()

    # 2) живой invite уже есть?
    res2 = await db.execute(
        select(Invite).where(
            Invite.email == email,
            Invite.used_at.is_(None),
            Invite.expires_at > datetime.now(UTC),
        )
    )
    existing = res2.scalar_one_or_none()
    if existing is not None:
        raise InviteAlreadyPending(existing_id=str(existing.id))

    invite = Invite(
        token=secrets.token_urlsafe(32),
        email=email,
        role=role,
        created_by_user_id=created_by.id,
        expires_at=datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    await db.flush()
    return invite


async def list_invites(db: AsyncSession, *, status: str = "all") -> list[Invite]:
    stmt = select(Invite).order_by(Invite.created_at.desc())
    now = datetime.now(UTC)
    if status == "active":
        stmt = stmt.where(Invite.used_at.is_(None), Invite.expires_at > now)
    elif status == "used":
        stmt = stmt.where(Invite.used_at.is_not(None))
    elif status == "expired":
        stmt = stmt.where(Invite.used_at.is_(None), Invite.expires_at <= now)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def cancel_invite(db: AsyncSession, invite_id: uuid.UUID, *, by_admin: User) -> None:
    invite = await db.get(Invite, invite_id)
    if invite is None:
        raise InviteInvalid("Приглашение не найдено.")
    if invite.used_at is not None:
        return  # идемпотентно
    invite.used_at = datetime.now(UTC)
    invite.used_by_user_id = by_admin.id
    await db.flush()
