"""Admin endpoint: GET /api/admin/jobs — все запуски всех юзеров."""
# ruff: noqa: B008, RUF002
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.job import JobListItemOut
from portal_api.services import job_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=list[JobListItemOut])
async def list_all_jobs(
    limit: int = 50,
    before: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[JobListItemOut]:
    """Все запуски всех юзеров. Cursor pagination как в /api/jobs."""
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be 1..200")
    return await job_service.list_all_jobs(db, limit=limit, before=before)
