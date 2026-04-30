"""Простые фабрики моделей для тестов."""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from portal_api.core.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Invite, User


class UserFactory:
    """Создаёт юзера с дефолтными значениями. Все поля переопределимы."""

    _counter = 0

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        *,
        email: str | None = None,
        password: str = "test-pass",
        display_name: str = "Test User",
        role: str = "user",
        **extra: Any,
    ) -> User:
        cls._counter += 1
        if email is None:
            email = f"user{cls._counter}-{secrets.token_hex(4)}@test.local"
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            display_name=display_name,
            role=role,
            **extra,
        )
        session.add(user)
        await session.flush()
        return user


class InviteFactory:
    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        *,
        created_by: User,
        email: str | None = None,
        token: str | None = None,
        expires_at: datetime | None = None,
        used_at: datetime | None = None,
        used_by: User | None = None,
    ) -> Invite:
        if email is None:
            email = f"invitee-{secrets.token_hex(4)}@test.local"
        if token is None:
            token = secrets.token_urlsafe(32)
        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(days=7)
        invite = Invite(
            token=token,
            email=email.lower(),
            created_by_user_id=created_by.id,
            expires_at=expires_at,
            used_at=used_at,
            used_by_user_id=used_by.id if used_by else None,
        )
        session.add(invite)
        await session.flush()
        return invite
