# ruff: noqa: B008
"""Публичные эндпоинты агентов: GET /api/agents и GET /api/agents/{slug}."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_current_user, get_db
from portal_api.models import AgentVersion, Tab, User
from portal_api.schemas.agent import (
    AgentCurrentVersionBrief,
    AgentDetailOut,
    AgentPublicOut,
    AgentTabBrief,
)
from portal_api.services.agent_service import get_public_agent_by_slug, list_public_agents

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentPublicOut])
async def get_agents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AgentPublicOut]:
    rows = await list_public_agents(db)
    return [_to_public_out(agent, version, tab) for agent, version, tab in rows]


@router.get("/agents/{slug}", response_model=AgentDetailOut)
async def get_agent_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AgentDetailOut:
    agent, version, tab = await get_public_agent_by_slug(db, slug)
    return AgentDetailOut(
        id=agent.id,
        slug=agent.slug,
        name=agent.name,
        icon=agent.icon,
        short_description=agent.short_description,
        tab=AgentTabBrief(slug=tab.slug, name=tab.name),
        current_version=AgentCurrentVersionBrief(
            id=version.id,
            manifest_version=version.manifest_version,
            git_sha=version.git_sha,
        ),
        manifest=version.manifest_jsonb,
    )


def _to_public_out(agent, version: AgentVersion, tab: Tab) -> AgentPublicOut:  # type: ignore[no-untyped-def]
    return AgentPublicOut(
        id=agent.id,
        slug=agent.slug,
        name=agent.name,
        icon=agent.icon,
        short_description=agent.short_description,
        tab=AgentTabBrief(slug=tab.slug, name=tab.name),
        current_version=AgentCurrentVersionBrief(
            id=version.id,
            manifest_version=version.manifest_version,
            git_sha=version.git_sha,
        ),
    )
