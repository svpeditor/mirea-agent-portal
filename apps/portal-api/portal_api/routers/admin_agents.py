# ruff: noqa: B008
"""Admin endpoints для агентов: создание + первая версия + enqueue билда."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.deps import get_build_enqueuer, get_db, require_admin
from portal_api.models import User
from portal_api.schemas.agent import AgentAdminOut, AgentCreateIn
from portal_api.schemas.agent_version import AgentVersionEnqueuedOut
from portal_api.services import agent_service
from portal_api.services.build_enqueue import BuildEnqueuer

router = APIRouter(
    prefix="/admin/agents",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreateIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    enqueuer: BuildEnqueuer = Depends(get_build_enqueuer),
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    agent, version = await agent_service.create_agent(
        db,
        git_url=str(payload.git_url),
        git_ref=payload.git_ref,
        settings=settings,
        created_by_user_id=admin.id,
    )
    await db.commit()
    await db.refresh(agent)
    await db.refresh(version)
    enqueuer.enqueue_build(version.id)
    return {
        "agent": AgentAdminOut.model_validate(agent).model_dump(mode="json"),
        "version": AgentVersionEnqueuedOut(
            id=version.id, status=version.status
        ).model_dump(mode="json"),
    }
