# ruff: noqa: RUF002, RUF003, S603, S607
"""Бизнес-логика для агентов: создание агента + первой версии.

Включает:
- shallow git-clone репозитория для парсинга manifest.yaml,
- валидацию manifest через portal_sdk.Manifest,
- проверку base_image против whitelist,
- lookup tab по manifest.category с fallback на uncategorized,
- создание Agent + AgentVersion со status='pending_build'.
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

import yaml
from portal_sdk.manifest import Manifest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings
from portal_api.core.exceptions import (
    AgentSlugTakenError,
    BaseImageNotAllowedError,
    ManifestInvalidError,
    ManifestNotFoundError,
    TabNotFoundError,
)
from portal_api.core.git_resolve import resolve_git_ref
from portal_api.models import Agent, AgentVersion, Tab

_CLONE_TIMEOUT_SECONDS = 60


def _shallow_clone_sync(git_url: str, git_sha: str) -> dict[str, Any]:
    """Синхронный shallow-clone + чтение manifest.yaml для указанного SHA."""
    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "repo"
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    "--no-single-branch",
                    git_url,
                    str(clone_dir),
                ],
                capture_output=True,
                check=True,
                timeout=_CLONE_TIMEOUT_SECONDS,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(clone_dir),
                    "fetch",
                    "--depth=1",
                    "origin",
                    git_sha,
                ],
                capture_output=True,
                check=True,
                timeout=_CLONE_TIMEOUT_SECONDS,
            )
            subprocess.run(
                ["git", "-C", str(clone_dir), "checkout", git_sha],
                capture_output=True,
                check=True,
                timeout=_CLONE_TIMEOUT_SECONDS,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise ManifestNotFoundError() from e

        manifest_path = clone_dir / "manifest.yaml"
        if not manifest_path.is_file():
            raise ManifestNotFoundError()
        try:
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ManifestInvalidError(message=f"manifest.yaml: невалидный YAML — {e}") from e
        if not isinstance(data, dict):
            raise ManifestInvalidError(
                message="manifest.yaml: ожидался объект на верхнем уровне."
            )
        return data


async def _shallow_clone_for_manifest(git_url: str, git_sha: str) -> dict[str, Any]:
    """Async обёртка вокруг sync shallow-clone (subprocess блокирует event loop)."""
    return await asyncio.to_thread(_shallow_clone_sync, git_url, git_sha)


async def _get_tab_for_category(session: AsyncSession, category: str) -> Tab:
    """Lookup Tab по manifest.category. Fallback на 'uncategorized', если категории нет."""
    res = await session.execute(select(Tab).where(Tab.slug == category))
    tab = res.scalar_one_or_none()
    if tab is not None:
        return tab
    res = await session.execute(select(Tab).where(Tab.slug == "uncategorized"))
    tab = res.scalar_one_or_none()
    if tab is None:
        # uncategorized должен существовать всегда (bootstrap_tabs).
        # Если его нет — это баг конфигурации.
        raise TabNotFoundError()
    return tab


async def create_agent(
    session: AsyncSession,
    *,
    git_url: str,
    git_ref: str,
    settings: Settings,
    created_by_user_id: uuid.UUID,
) -> tuple[Agent, AgentVersion]:
    """Создать Agent + первую AgentVersion (status='pending_build').

    Алгоритм:
      1. resolve_git_ref(git_url, git_ref) → git_sha.
      2. shallow-clone репо на этом SHA, прочитать manifest.yaml.
      3. Валидировать через Manifest.model_validate; проверить base_image.
      4. Найти Tab по manifest.category (fallback uncategorized).
      5. Создать Agent (enabled=False, current_version_id=None) + AgentVersion.
    """
    # 1. Резолюция SHA
    git_sha = await resolve_git_ref(git_url, git_ref)

    # 2. shallow-clone + парс manifest
    manifest_data = await _shallow_clone_for_manifest(git_url, git_sha)

    # 3. Валидация manifest + base_image
    try:
        manifest = Manifest.model_validate(manifest_data)
    except ValidationError as e:
        raise ManifestInvalidError(
            message=f"manifest.yaml не прошёл валидацию: {e.error_count()} ошибок."
        ) from e

    base_image = manifest.runtime.docker.base_image
    if base_image not in settings.allowed_base_images:
        raise BaseImageNotAllowedError(base_image)

    # 4. Lookup tab
    category = (
        manifest.category.value
        if hasattr(manifest.category, "value")
        else str(manifest.category)
    )
    tab = await _get_tab_for_category(session, category)

    # 5. Создать Agent + AgentVersion
    agent = Agent(
        slug=manifest.id,
        name=manifest.name,
        icon=manifest.icon,
        short_description=manifest.short_description,
        tab_id=tab.id,
        current_version_id=None,
        enabled=False,
        git_url=git_url,
        created_by_user_id=created_by_user_id,
    )
    session.add(agent)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "agents_slug_key" in str(e.orig):
            raise AgentSlugTakenError() from e
        raise

    manifest_snapshot = manifest.model_dump(mode="json")
    version = AgentVersion(
        agent_id=agent.id,
        git_sha=git_sha,
        git_ref=git_ref,
        manifest_jsonb=manifest_snapshot,
        manifest_version=manifest.version,
        docker_image_tag=None,
        status="pending_build",
        created_by_user_id=created_by_user_id,
    )
    session.add(version)
    await session.flush()
    return agent, version
