# ruff: noqa: B008
"""Публичный эндпоинт списка вкладок: GET /api/tabs."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_current_user, get_db
from portal_api.models import User
from portal_api.schemas.tab import TabOut
from portal_api.services.tab_service import list_public_tabs

router = APIRouter(tags=["tabs"])


@router.get("/tabs", response_model=list[TabOut])
async def get_tabs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TabOut]:
    tabs = await list_public_tabs(db)
    return [TabOut.model_validate(t) for t in tabs]
