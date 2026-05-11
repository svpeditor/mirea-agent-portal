# ruff: noqa: B008
"""Эндпоинты /api/me — текущий юзер."""
from __future__ import annotations

import base64
import json as _json
import uuid as _uuid
from datetime import datetime
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.deps import get_current_user, get_db
from portal_api.models import Agent, AgentVersion, UsageLog, User
from portal_api.models.llm import UserQuota
from portal_api.schemas.llm import UsageLogItemSchema, UsagePageSchema, UserQuotaSchema
from portal_api.schemas.user import ChangePasswordIn, UserOut, UserUpdate
from portal_api.services import user_service
from portal_api.services.file_store import LocalDiskFileStore

_AVATAR_ALLOWED_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
_AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=None)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    quota = await db.get(UserQuota, user.id)
    user_out = UserOut.model_validate(user)
    result = user_out.model_dump(mode="json")
    result["quota"] = (
        UserQuotaSchema.model_validate(quota).model_dump(mode="json") if quota else None
    )
    return result


@router.patch("", response_model=UserOut)
async def patch_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if payload.display_name is not None:
        await user_service.update_display_name(db, user, payload.display_name)
    if payload.notify_on_job_finish is not None:
        user.notify_on_job_finish = payload.notify_on_job_finish
        await db.flush()
    await db.commit()
    await db.refresh(user)
    return user


async def _stream_upload(upload: UploadFile, limit: int):
    """Async-iterator: чанками с upload.read() с защитой по размеру."""
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            return
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail={"error": {"code": "AVATAR_TOO_LARGE", "message": f"Файл больше {limit // 1024 // 1024} МБ."}},
            )
        yield chunk


@router.post("/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    ct = (file.content_type or "").lower()
    if ct not in _AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "AVATAR_BAD_TYPE",
                    "message": f"Поддерживаются только {', '.join(sorted(_AVATAR_ALLOWED_TYPES))}.",
                }
            },
        )
    store = LocalDiskFileStore(root=settings.file_store_local_root)
    # Уникальный ключ — uuid4 чтобы CDN/браузер не закешировал старую картинку.
    key = f"avatars/{user.id}/{_uuid.uuid4().hex}"
    await store.put(key, _stream_upload(file, _AVATAR_MAX_BYTES))
    # Удалить старый ключ, если был.
    if user.avatar_storage_key and user.avatar_storage_key != key:
        try:
            await store.delete(user.avatar_storage_key)
        except Exception:  # noqa: BLE001
            pass
    user.avatar_storage_key = key
    user.avatar_content_type = ct
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/avatar", response_model=UserOut)
async def delete_avatar(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if user.avatar_storage_key:
        store = LocalDiskFileStore(root=settings.file_store_local_root)
        try:
            await store.delete(user.avatar_storage_key)
        except Exception:  # noqa: BLE001
            pass
    user.avatar_storage_key = None
    user.avatar_content_type = None
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/avatar")
async def get_my_avatar(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    if not user.avatar_storage_key:
        raise HTTPException(status_code=404, detail={"error": {"code": "AVATAR_NOT_FOUND"}})
    store = LocalDiskFileStore(root=settings.file_store_local_root)
    return StreamingResponse(
        store.get(user.avatar_storage_key),
        media_type=user.avatar_content_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )


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


@router.get("/usage", response_model=UsagePageSchema)
async def me_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
) -> UsagePageSchema:
    stmt = (
        sa.select(UsageLog, Agent.slug)
        .join(AgentVersion, AgentVersion.id == UsageLog.agent_version_id)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .where(UsageLog.user_id == current_user.id)
        .order_by(UsageLog.created_at.desc(), UsageLog.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        try:
            decoded = _json.loads(base64.urlsafe_b64decode(cursor + "==").decode())
            cur_ts = datetime.fromisoformat(decoded["ts"])
            cur_id = decoded["id"]
        except (ValueError, KeyError, _json.JSONDecodeError):
            cur_ts, cur_id = None, None
        if cur_ts is not None:
            stmt = stmt.where(
                sa.or_(
                    UsageLog.created_at < cur_ts,
                    sa.and_(UsageLog.created_at == cur_ts, UsageLog.id < cur_id),
                )
            )
    if from_ is not None:
        stmt = stmt.where(UsageLog.created_at >= from_)
    if to is not None:
        stmt = stmt.where(UsageLog.created_at <= to)

    rows = (await db.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    items = []
    for log, slug in page:
        item = UsageLogItemSchema.model_validate(log)
        item = item.model_copy(update={"agent_slug": slug})
        items.append(item)

    next_cursor = None
    if has_more and page:
        last_log = page[-1][0]
        cursor_payload = _json.dumps({
            "ts": last_log.created_at.isoformat(),
            "id": str(last_log.id),
        })
        next_cursor = base64.urlsafe_b64encode(cursor_payload.encode()).decode().rstrip("=")

    return UsagePageSchema(items=items, next_cursor=next_cursor)
