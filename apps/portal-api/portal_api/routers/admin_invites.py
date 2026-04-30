# ruff: noqa: B008
"""Admin endpoints для invite-токенов."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.invite import (
    InviteCreateIn,
    InviteCreateOut,
    InviteOut,
    InvitesListOut,
)
from portal_api.services import invite_service

router = APIRouter(prefix="/admin/invites", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post(
    "",
    response_model=InviteCreateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    payload: InviteCreateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> InviteCreateOut:
    invite = await invite_service.create_invite(
        db, email=payload.email, created_by=admin
    )
    base = str(request.base_url).rstrip("/")
    registration_url = f"{base}/register?token={invite.token}"
    return InviteCreateOut(
        id=invite.id,
        token=invite.token,
        email=invite.email,
        expires_at=invite.expires_at,
        registration_url=registration_url,
    )


@router.get("", response_model=InvitesListOut)
async def list_invites(
    status_: str = Query(default="all", alias="status"),
    db: AsyncSession = Depends(get_db),
) -> InvitesListOut:
    invites = await invite_service.list_invites(db, status=status_)
    return InvitesListOut(invites=[InviteOut.model_validate(i) for i in invites])


@router.delete("/{invite_id}")
async def cancel_invite(
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    await invite_service.cancel_invite(db, invite_id, by_admin=admin)
    return {"status": "ok"}
