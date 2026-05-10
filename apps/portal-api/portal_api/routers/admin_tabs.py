# ruff: noqa: B008
"""Admin endpoints CRUD для вкладок."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.tab import TabAdminOut, TabCreateIn, TabUpdateIn
from portal_api.services import audit_service, tab_service
from portal_api.services.audit_service import A as Action

router = APIRouter(
    prefix="/admin/tabs",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[TabAdminOut])
async def list_tabs(
    db: AsyncSession = Depends(get_db),
) -> list[TabAdminOut]:
    tabs = await tab_service.list_admin_tabs(db)
    return [TabAdminOut.model_validate(t) for t in tabs]


@router.post(
    "",
    response_model=TabAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_tab(
    payload: TabCreateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> TabAdminOut:
    tab = await tab_service.create_tab(
        db,
        slug=payload.slug,
        name=payload.name,
        icon=payload.icon,
        order_idx=payload.order_idx,
    )
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.TAB_CREATE,
        resource_type="tab",
        resource_id=str(tab.id),
        payload={"slug": payload.slug, "name": payload.name},
        ip=ip,
        user_agent=ua,
    )
    return TabAdminOut.model_validate(tab)


@router.patch("/{tab_id}", response_model=TabAdminOut)
async def update_tab(
    tab_id: uuid.UUID,
    payload: TabUpdateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> TabAdminOut:
    tab = await tab_service.update_tab(
        db,
        tab_id,
        name=payload.name,
        icon=payload.icon,
        order_idx=payload.order_idx,
    )
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.TAB_UPDATE,
        resource_type="tab",
        resource_id=str(tab_id),
        payload=payload.model_dump(exclude_none=True, mode="json"),
        ip=ip,
        user_agent=ua,
    )
    return TabAdminOut.model_validate(tab)


@router.delete("/{tab_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tab(
    tab_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    await tab_service.delete_tab(db, tab_id)
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.TAB_DELETE,
        resource_type="tab",
        resource_id=str(tab_id),
        ip=ip,
        user_agent=ua,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
