# ruff: noqa: B008
"""Admin endpoints CRUD для вкладок."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.schemas.tab import TabAdminOut, TabCreateIn, TabUpdateIn
from portal_api.services import tab_service

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
    db: AsyncSession = Depends(get_db),
) -> TabAdminOut:
    tab = await tab_service.create_tab(
        db,
        slug=payload.slug,
        name=payload.name,
        icon=payload.icon,
        order_idx=payload.order_idx,
    )
    return TabAdminOut.model_validate(tab)


@router.patch("/{tab_id}", response_model=TabAdminOut)
async def update_tab(
    tab_id: uuid.UUID,
    payload: TabUpdateIn,
    db: AsyncSession = Depends(get_db),
) -> TabAdminOut:
    tab = await tab_service.update_tab(
        db,
        tab_id,
        name=payload.name,
        icon=payload.icon,
        order_idx=payload.order_idx,
    )
    return TabAdminOut.model_validate(tab)


@router.delete("/{tab_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tab(
    tab_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await tab_service.delete_tab(db, tab_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
