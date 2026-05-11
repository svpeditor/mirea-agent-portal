# ruff: noqa: B008
"""Admin endpoints для агентов: CRUD + создание + первая версия + enqueue билда."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.deps import get_build_enqueuer, get_db, require_admin
from portal_api.models import User
from portal_api.schemas.agent import (
    AgentAdminOut,
    AgentCreateIn,
    AgentLatestVersionAdminBrief,
    AgentUpdateIn,
)
from portal_api.schemas.agent_version import AgentVersionEnqueuedOut
from portal_api.services import agent_service, audit_service
from portal_api.services.audit_service import A as Action
from portal_api.services.build_enqueue import BuildEnqueuer

router = APIRouter(
    prefix="/admin/agents",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[AgentAdminOut])
async def list_agents(
    tab_id: uuid.UUID | None = None,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[AgentAdminOut]:
    pairs = await agent_service.list_admin_agents(db, tab_id=tab_id, enabled=enabled)
    out: list[AgentAdminOut] = []
    for agent, latest in pairs:
        item = AgentAdminOut.model_validate(agent)
        if latest is not None:
            item.latest_version = AgentLatestVersionAdminBrief(
                id=latest.id,
                status=latest.status,
                git_sha=latest.git_sha,
                created_at=latest.created_at,
            )
        out.append(item)
    return out


@router.get("/{agent_id}", response_model=AgentAdminOut)
async def get_agent_endpoint(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentAdminOut:
    agent = await agent_service.get_agent(db, agent_id)
    pairs = await agent_service.list_admin_agents(db)
    latest = next((v for a, v in pairs if a.id == agent.id), None)
    item = AgentAdminOut.model_validate(agent)
    if latest is not None:
        item.latest_version = AgentLatestVersionAdminBrief(
            id=latest.id,
            status=latest.status,
            git_sha=latest.git_sha,
            created_at=latest.created_at,
        )
    return item


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreateIn,
    request: Request,
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
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.AGENT_CREATE,
        resource_type="agent",
        resource_id=str(agent.id),
        payload={"git_url": str(payload.git_url), "git_ref": payload.git_ref},
        ip=ip,
        user_agent=ua,
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


@router.patch("/{agent_id}", response_model=AgentAdminOut)
async def update_agent_endpoint(
    agent_id: uuid.UUID,
    payload: AgentUpdateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AgentAdminOut:
    agent = await agent_service.update_agent(
        db,
        agent_id,
        tab_id=payload.tab_id,
        enabled=payload.enabled,
    )
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.AGENT_UPDATE,
        resource_type="agent",
        resource_id=str(agent_id),
        payload=payload.model_dump(exclude_none=True, mode="json"),
        ip=ip,
        user_agent=ua,
    )
    return AgentAdminOut.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_endpoint(
    agent_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    await agent_service.delete_agent(db, agent_id)
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.AGENT_DELETE,
        resource_type="agent",
        resource_id=str(agent_id),
        ip=ip,
        user_agent=ua,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
