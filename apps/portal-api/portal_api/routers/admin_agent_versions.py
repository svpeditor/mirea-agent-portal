# ruff: noqa: B008
"""Admin endpoints для agent_versions: list/get/new/set_current/retry/delete."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_build_enqueuer, get_db, require_admin
from portal_api.models import User
from portal_api.schemas.agent import AgentAdminOut
from portal_api.schemas.agent_version import (
    AgentVersionDetailOut,
    AgentVersionListItemOut,
    NewVersionIn,
)
from portal_api.services import agent_version_service as svc
from portal_api.services.build_enqueue import BuildEnqueuer

router = APIRouter(tags=["admin-agent-versions"], dependencies=[Depends(require_admin)])


@router.get(
    "/admin/agents/{agent_id}/versions",
    response_model=list[AgentVersionListItemOut],
)
async def list_versions(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AgentVersionListItemOut]:
    rows = await svc.list_versions_for_agent(db, agent_id)
    out: list[AgentVersionListItemOut] = []
    for v, is_current in rows:
        item = AgentVersionListItemOut.model_validate(v)
        item.is_current = is_current
        out.append(item)
    return out


@router.get(
    "/admin/agent_versions/{version_id}",
    response_model=AgentVersionDetailOut,
)
async def get_version_endpoint(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentVersionDetailOut:
    v, is_current = await svc.get_version(db, version_id)
    out = AgentVersionDetailOut.model_validate(v)
    out.is_current = is_current
    return out


@router.post(
    "/admin/agents/{agent_id}/versions",
    response_model=AgentVersionDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def new_version(
    agent_id: uuid.UUID,
    payload: NewVersionIn,
    db: AsyncSession = Depends(get_db),
    enqueuer: BuildEnqueuer = Depends(get_build_enqueuer),
    admin: User = Depends(require_admin),
) -> AgentVersionDetailOut:
    v = await svc.create_new_version(
        db, agent_id, git_ref=payload.git_ref, created_by_user_id=admin.id
    )
    await db.commit()
    await db.refresh(v)
    enqueuer.enqueue_build(v.id)
    out = AgentVersionDetailOut.model_validate(v)
    out.is_current = False
    return out


@router.post(
    "/admin/agent_versions/{version_id}/set_current",
    response_model=AgentAdminOut,
)
async def set_current_endpoint(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentAdminOut:
    agent = await svc.set_current(db, version_id)
    await db.commit()
    await db.refresh(agent)
    return AgentAdminOut.model_validate(agent)


@router.post(
    "/admin/agent_versions/{version_id}/retry",
    response_model=AgentVersionDetailOut,
)
async def retry_endpoint(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    enqueuer: BuildEnqueuer = Depends(get_build_enqueuer),
) -> AgentVersionDetailOut:
    v = await svc.retry_version(db, version_id)
    await db.commit()
    await db.refresh(v)
    enqueuer.enqueue_build(v.id)
    out = AgentVersionDetailOut.model_validate(v)
    out.is_current = False
    return out


@router.delete(
    "/admin/agent_versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_version_endpoint(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    image_tag = await svc.delete_version(db, version_id)
    await db.commit()
    if image_tag:
        # Best-effort cleanup; ошибки в логи, не в response.
        try:
            import docker  # type: ignore[import-untyped]

            docker.from_env().images.remove(image_tag, force=True)
        except Exception:
            import structlog

            structlog.get_logger().warning(
                "docker_rmi_failed", image_tag=image_tag, exc_info=True
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
