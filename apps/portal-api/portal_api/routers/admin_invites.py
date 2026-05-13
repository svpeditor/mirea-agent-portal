# ruff: noqa: B008
"""Admin endpoints для invite-токенов."""
from __future__ import annotations

import os
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
from portal_api.services import audit_service, invite_service
from portal_api.services.audit_service import A as Action

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
        db, email=payload.email, created_by=admin, role=payload.role
    )
    # PUBLIC_BASE_URL переопределяет request.base_url, когда API стоит за обратным
    # прокси (Next.js / Tailscale Funnel / nginx) - тогда base_url видит внутренний
    # хост типа http://api:8000 и инвайт-ссылка получается нерабочей.
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or str(request.base_url).rstrip("/")
    registration_url = f"{base}/register?invite={invite.token}"

    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.INVITE_CREATE,
        resource_type="invite",
        resource_id=str(invite.id),
        payload={"email": invite.email},
        ip=ip,
        user_agent=ua,
    )

    return InviteCreateOut(
        id=invite.id,
        token=invite.token,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        registration_url=registration_url,
    )


@router.get("", response_model=InvitesListOut)
async def list_invites(
    request: Request,
    status_: str = Query(default="all", alias="status"),
    db: AsyncSession = Depends(get_db),
) -> InvitesListOut:
    invites = await invite_service.list_invites(db, status=status_)
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or str(request.base_url).rstrip("/")
    items = []
    for inv in invites:
        out = InviteOut.model_validate(inv)
        out.registration_url = f"{base}/register?invite={inv.token}"
        items.append(out)
    return InvitesListOut(invites=items)


@router.delete("/{invite_id}")
async def cancel_invite(
    invite_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    await invite_service.cancel_invite(db, invite_id, by_admin=admin)

    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.INVITE_REVOKE,
        resource_type="invite",
        resource_id=str(invite_id),
        ip=ip,
        user_agent=ua,
    )

    return {"status": "ok"}
