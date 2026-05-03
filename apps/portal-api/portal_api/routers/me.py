# ruff: noqa: B008
"""Эндпоинты /api/me — текущий юзер."""
from __future__ import annotations

import base64
import json as _json
from datetime import datetime
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Cookie, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_current_user, get_db
from portal_api.models import Agent, AgentVersion, UsageLog, User
from portal_api.models.llm import UserQuota
from portal_api.schemas.llm import UsageLogItemSchema, UsagePageSchema, UserQuotaSchema
from portal_api.schemas.user import ChangePasswordIn, UserOut, UserUpdate
from portal_api.services import user_service

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
