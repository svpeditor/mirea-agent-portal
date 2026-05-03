# ruff: noqa: B008
"""Admin endpoints для управления юзерами."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portal_api.deps import get_db, require_admin
from portal_api.models import User, UserQuota
from portal_api.schemas.user import ResetPasswordOut, UserAdminOut, UserAdminUpdate, UserOut
from portal_api.services import user_service

router = APIRouter(
    prefix="/admin/users", tags=["admin"], dependencies=[Depends(require_admin)]
)


class UsersListOut(BaseModel):
    users: list[UserOut]
    next_cursor: str | None = None


@router.get("", response_model=UsersListOut)
async def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> UsersListOut:
    users = await user_service.list_users(db, limit=limit, cursor=cursor)
    next_cursor = str(users[-1].id) if len(users) == limit else None
    return UsersListOut(
        users=[UserOut.model_validate(u) for u in users],
        next_cursor=next_cursor,
    )


@router.get("/{user_id}", response_model=UserAdminOut)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> User:
    stmt = (
        sa.select(User)
        .where(User.id == user_id)
        .options(selectinload(User.quota))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        from portal_api.core.exceptions import UserNotFound
        raise UserNotFound()
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: uuid.UUID,
    payload: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_service.update_user_admin(
        db,
        user_id,
        display_name=payload.display_name,
        role=payload.role,
        monthly_budget_usd=payload.monthly_budget_usd,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await user_service.delete_user(db, user_id)
    return {"status": "ok"}


@router.post("/{user_id}/reset-password", response_model=ResetPasswordOut)
async def reset_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResetPasswordOut:
    new_pwd = await user_service.reset_password(db, user_id)
    return ResetPasswordOut(temporary_password=new_pwd)
