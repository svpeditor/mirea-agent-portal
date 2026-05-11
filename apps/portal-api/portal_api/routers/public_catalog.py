"""Публичный каталог для landing-страницы: без авторизации.

Отдаёт минимум, нужный для рендера превью на главной — slug, name,
короткое описание, категория. Без runtime/manifest/секретов.
"""
# ruff: noqa: B008, RUF001, RUF002
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db
from portal_api.services.agent_service import list_public_agents

router = APIRouter(tags=["public"])


class PublicCatalogAgent(BaseModel):
    slug: str
    name: str
    short_description: str
    icon: str | None
    category: str  # tab.name
    category_slug: str  # tab.slug


class PublicCatalogOut(BaseModel):
    agents: list[PublicCatalogAgent]
    total_agents: int


@router.get("/public/catalog", response_model=PublicCatalogOut)
async def public_catalog(
    limit: int = 3,
    db: AsyncSession = Depends(get_db),
) -> PublicCatalogOut:
    """Список включённых агентов для landing. По умолчанию первые 3."""
    rows = await list_public_agents(db)
    items: list[PublicCatalogAgent] = []
    for agent, _version, tab in rows[:limit]:
        items.append(
            PublicCatalogAgent(
                slug=agent.slug,
                name=agent.name,
                short_description=agent.short_description,
                icon=agent.icon,
                category=tab.name,
                category_slug=tab.slug,
            )
        )
    return PublicCatalogOut(agents=items, total_agents=len(rows))
