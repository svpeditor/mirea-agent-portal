"""Admin audit log endpoint: GET /api/admin/audit."""
# ruff: noqa: B008
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
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


@router.post("/audit/cleanup")
async def cleanup_audit(
    days: int = 365,
    request: Request = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, int]:
    """Удалить audit-записи старше N дней. По умолчанию 365.

    Минимум — 30 дней (защита от accidental wipe). Возвращает {"deleted": N}.
    """
    if days < 30:
        raise HTTPException(status_code=400, detail="days must be >= 30")
    deleted = await audit_service.cleanup_older_than(db, days=days)
    # Сам факт cleanup пишется в audit log
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action="audit.cleanup",
        resource_type="audit",
        payload={"days": days, "deleted": deleted},
        ip=ip,
        user_agent=ua,
    )
    return {"deleted": deleted}
