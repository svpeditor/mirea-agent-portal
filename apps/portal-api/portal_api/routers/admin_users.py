# ruff: noqa: B008
"""Admin endpoints для управления юзерами."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portal_api.config import Settings, get_settings
from portal_api.core.exceptions import AppError
from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.user import ResetPasswordOut, UserAdminOut, UserAdminUpdate, UserOut
from portal_api.services import audit_service, user_service
from portal_api.services.audit_service import A as Action
from portal_api.services.file_store import LocalDiskFileStore

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
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    if payload.role is not None and user_id == admin.id:
        raise AppError(
            code="CANNOT_CHANGE_OWN_ROLE",
            message="Нельзя менять собственную роль",
            status_code=400,
        )
    user = await user_service.update_user_admin(
        db,
        user_id,
        display_name=payload.display_name,
        role=payload.role,
        monthly_budget_usd=payload.monthly_budget_usd,
    )
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.USER_UPDATE_QUOTA,
        resource_type="user",
        resource_id=str(user_id),
        payload=payload.model_dump(exclude_none=True, mode="json"),
        ip=ip,
        user_agent=ua,
    )
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    await user_service.delete_user(db, user_id)
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.USER_DELETE,
        resource_type="user",
        resource_id=str(user_id),
        ip=ip,
        user_agent=ua,
    )
    return {"status": "ok"}


@router.post("/{user_id}/reset-password", response_model=ResetPasswordOut)
async def reset_password(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ResetPasswordOut:
    new_pwd = await user_service.reset_password(db, user_id)
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.USER_RESET_PASSWORD,
        resource_type="user",
        resource_id=str(user_id),
        ip=ip,
        user_agent=ua,
    )
    return ResetPasswordOut(temporary_password=new_pwd)


@router.get("/{user_id}/avatar")
async def get_user_avatar(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Стрим аватара любого юзера (admin-only — gate уже на роутере)."""
    user = await db.get(User, user_id)
    if user is None or not user.avatar_storage_key:
        raise HTTPException(status_code=404, detail={"error": {"code": "AVATAR_NOT_FOUND"}})
    store = LocalDiskFileStore(root=settings.file_store_local_root)
    return StreamingResponse(
        store.get(user.avatar_storage_key),
        media_type=user.avatar_content_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )
