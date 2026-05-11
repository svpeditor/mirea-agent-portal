"""Admin audit log endpoint: GET /api/admin/audit."""
# ruff: noqa: B008
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.audit import AuditLogOut
from portal_api.services import audit_service

router = APIRouter(prefix="/admin", tags=["admin", "audit"])


@router.get("/audit", response_model=list[AuditLogOut])
async def list_audit(
    limit: int = 50,
    before: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AuditLogOut]:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be 1..200")
    rows = await audit_service.list_audit(
        db,
        limit=limit,
        before=before,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
    )
    return [AuditLogOut.from_orm_row(r) for r in rows]
