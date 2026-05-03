"""Простые фабрики моделей для тестов."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.security import hash_password
from portal_api.models import Agent, AgentVersion, Invite, Job, Tab, User


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
            email = f"user{cls._counter}-{secrets.token_hex(4)}@example.com"
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
            email = f"invitee-{secrets.token_hex(4)}@example.com"
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


_tab_counter = 0
_agent_counter = 0


async def make_tab(
    session: AsyncSession,
    *,
    slug: str | None = None,
    name: str | None = None,
    icon: str | None = None,
    order_idx: int = 0,
    is_system: bool = False,
) -> Tab:
    """Создать вкладку с дефолтами. Все поля переопределимы."""
    global _tab_counter
    _tab_counter += 1
    if slug is None:
        slug = f"tab-{_tab_counter}-{secrets.token_hex(4)}"
    if name is None:
        name = f"Tab {_tab_counter}"
    now = datetime.now(UTC)
    tab = Tab(
        id=uuid.uuid4(),
        slug=slug,
        name=name,
        icon=icon,
        order_idx=order_idx,
        is_system=is_system,
        created_at=now,
        updated_at=now,
    )
    session.add(tab)
    await session.flush()
    return tab


async def make_agent(
    session: AsyncSession,
    *,
    slug: str,
    tab_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    name: str | None = None,
    short_description: str = "test agent",
    enabled: bool = False,
    current_version_id: uuid.UUID | None = None,
    icon: str | None = None,
    git_url: str = "https://example.com/x.git",
) -> Agent:
    """Создать агента. По умолчанию disabled, без current_version."""
    global _agent_counter
    _agent_counter += 1
    if name is None:
        name = f"Agent {_agent_counter}"
    now = datetime.now(UTC)
    agent = Agent(
        id=uuid.uuid4(),
        slug=slug,
        name=name,
        icon=icon,
        short_description=short_description,
        tab_id=tab_id,
        current_version_id=current_version_id,
        enabled=enabled,
        git_url=git_url,
        created_by_user_id=created_by_user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(agent)
    await session.flush()
    return agent


async def make_agent_version(
    session: AsyncSession,
    *,
    agent_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    git_sha: str | None = None,
    git_ref: str = "main",
    manifest_jsonb: dict[str, Any] | None = None,
    manifest_version: str = "1.0",
    docker_image_tag: str | None = None,
    status: str = "ready",
) -> AgentVersion:
    """Создать версию агента. По умолчанию status='ready'."""
    if git_sha is None:
        git_sha = secrets.token_hex(20)
    if manifest_jsonb is None:
        manifest_jsonb = {"name": "test", "version": manifest_version}
    now = datetime.now(UTC)
    version = AgentVersion(
        id=uuid.uuid4(),
        agent_id=agent_id,
        git_sha=git_sha,
        git_ref=git_ref,
        manifest_jsonb=manifest_jsonb,
        manifest_version=manifest_version,
        docker_image_tag=docker_image_tag,
        status=status,
        created_by_user_id=created_by_user_id,
        created_at=now,
    )
    session.add(version)
    await session.flush()
    return version


async def make_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    password: str = "test-pass",
    display_name: str = "Test User",
    role: str = "user",
) -> User:
    """Создать юзера с дефолтами. Все поля переопределимы."""
    return await UserFactory.create(
        session, email=email, password=password, display_name=display_name, role=role,
    )


async def make_job(
    session: AsyncSession,
    *,
    agent_version_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str = "queued",
    params_jsonb: dict[str, Any] | None = None,
) -> Job:
    """Создать job с дефолтами."""
    if params_jsonb is None:
        params_jsonb = {}
    now = datetime.now(UTC)
    job = Job(
        id=uuid.uuid4(),
        agent_version_id=agent_version_id,
        created_by_user_id=user_id,
        status=status,
        params_jsonb=params_jsonb,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    await session.flush()
    return job
