# ruff: noqa: RUF002
"""Сервисы для работы с agent_versions.

Включает:
- list_versions_for_agent — список версий + флаг is_current,
- get_version — единичная версия + is_current,
- create_new_version — резолв SHA + shallow-clone + валидация manifest + INSERT,
- set_current — пометить версию как current и скопировать кеш-поля в Agent,
- retry_version — сбросить статус failed-версии в pending_build,
- delete_version — удалить версию (best-effort docker rmi делает router).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from portal_sdk.manifest import Manifest
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import (
    AgentNotFoundError,
    ManifestInvalidError,
    RetryNotFailedError,
    VersionAlreadyExistsError,
    VersionIsCurrentError,
    VersionNotFoundError,
    VersionNotReadyError,
)
from portal_api.core.git_resolve import resolve_git_ref
from portal_api.models import Agent, AgentVersion
from portal_api.services.agent_service import _shallow_clone_for_manifest


async def list_versions_for_agent(
    session: AsyncSession, agent_id: uuid.UUID
) -> list[tuple[AgentVersion, bool]]:
    """Список всех версий агента + флаг is_current. Order by created_at DESC."""
    agent = (
        await session.execute(select(Agent).where(Agent.id == agent_id))
    ).scalar_one_or_none()
    if agent is None:
        raise AgentNotFoundError()
    rows = list(
        (
            await session.execute(
                select(AgentVersion)
                .where(AgentVersion.agent_id == agent_id)
                .order_by(desc(AgentVersion.created_at))
            )
        )
        .scalars()
        .all()
    )
    return [(v, v.id == agent.current_version_id) for v in rows]


async def get_version(
    session: AsyncSession, version_id: uuid.UUID
) -> tuple[AgentVersion, bool]:
    """Единичная версия + is_current. 404 если нет."""
    v = (
        await session.execute(
            select(AgentVersion).where(AgentVersion.id == version_id)
        )
    ).scalar_one_or_none()
    if v is None:
        raise VersionNotFoundError()
    agent = (
        await session.execute(select(Agent).where(Agent.id == v.agent_id))
    ).scalar_one()
    return v, (v.id == agent.current_version_id)


async def create_new_version(
    session: AsyncSession,
    agent_id: uuid.UUID,
    *,
    git_ref: str,
    created_by_user_id: uuid.UUID,
) -> AgentVersion:
    """Создать новую версию агента (status='pending_build')."""
    agent = (
        await session.execute(select(Agent).where(Agent.id == agent_id))
    ).scalar_one_or_none()
    if agent is None:
        raise AgentNotFoundError()

    git_sha = await resolve_git_ref(agent.git_url, git_ref)
    manifest_data = await _shallow_clone_for_manifest(agent.git_url, git_sha)
    try:
        manifest = Manifest.model_validate(manifest_data)
    except ValidationError as exc:
        raise ManifestInvalidError(
            message=f"manifest.yaml не прошёл валидацию: {exc.error_count()} ошибок."
        ) from exc

    manifest_snapshot = manifest.model_dump(mode="json")
    v = AgentVersion(
        agent_id=agent.id,
        git_sha=git_sha,
        git_ref=git_ref,
        manifest_jsonb=manifest_snapshot,
        manifest_version=manifest.version,
        docker_image_tag=None,
        status="pending_build",
        created_by_user_id=created_by_user_id,
    )
    session.add(v)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        if "agent_versions_agent_id_git_sha_key" in str(exc.orig):
            raise VersionAlreadyExistsError() from exc
        raise
    return v


async def set_current(session: AsyncSession, version_id: uuid.UUID) -> Agent:
    """Сделать версию current. 409 если status≠ready. Копирует name/icon/short_desc."""
    v, _ = await get_version(session, version_id)
    if v.status != "ready":
        raise VersionNotReadyError()
    agent = (
        await session.execute(select(Agent).where(Agent.id == v.agent_id))
    ).scalar_one()
    agent.current_version_id = v.id
    m = v.manifest_jsonb
    agent.name = m["name"]
    agent.icon = m.get("icon")
    agent.short_description = m["short_description"]
    agent.updated_at = datetime.now(UTC)
    await session.flush()
    return agent


async def retry_version(
    session: AsyncSession, version_id: uuid.UUID
) -> AgentVersion:
    """Сбросить failed-версию в pending_build. 400 если не failed."""
    v, _ = await get_version(session, version_id)
    if v.status != "failed":
        raise RetryNotFailedError()
    v.status = "pending_build"
    v.build_log = None
    v.build_error = None
    v.build_started_at = None
    v.build_finished_at = None
    await session.flush()
    return v


async def delete_version(
    session: AsyncSession, version_id: uuid.UUID
) -> str | None:
    """Удалить версию. 409 если current. Возвращает image_tag для best-effort rmi."""
    v, is_current = await get_version(session, version_id)
    if is_current:
        raise VersionIsCurrentError()
    image_tag = v.docker_image_tag
    await session.delete(v)
    await session.flush()
    return image_tag
