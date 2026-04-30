# ruff: noqa: B008
"""Эндпоинты /api/me — текущий юзер."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_current_user, get_db
from portal_api.models import User
from portal_api.schemas.user import ChangePasswordIn, UserOut, UserUpdate
from portal_api.services import user_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("", response_model=UserOut)
async def patch_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if payload.display_name is not None:
        await user_service.update_display_name(db, user, payload.display_name)
    return user


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> dict[str, str]:
    await user_service.change_password(
        db,
        user,
        payload.current_password,
        payload.new_password,
        keep_refresh_raw=refresh_token,
    )
    return {"status": "ok"}
