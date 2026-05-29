# ruff: noqa: B008
"""Admin-обзор общей базы агентов: список датасетов, записи, удаление."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.dataset import DatasetAdminOut, DatasetRecordAdminOut
from portal_api.services import audit_service, dataset_service
from portal_api.services.audit_service import A as Action

router = APIRouter(
    prefix="/admin/datasets",
    tags=["admin-datasets"],
    dependencies=[Depends(require_admin)],
)

Slug = Annotated[
    str, Path(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=80)
]


@router.get("", response_model=list[DatasetAdminOut])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
) -> list[DatasetAdminOut]:
    pairs = await dataset_service.list_datasets(db)
    return [
        DatasetAdminOut(
            id=ds.id, slug=ds.slug, description=ds.description,
            record_count=cnt, created_at=ds.created_at, updated_at=ds.updated_at,
        )
        for ds, cnt in pairs
    ]


@router.get("/{slug}/records", response_model=list[DatasetRecordAdminOut])
async def list_dataset_records(
    slug: Slug,
    db: AsyncSession = Depends(get_db),
    prefix: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=dataset_service.MAX_LIST_LIMIT)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DatasetRecordAdminOut]:
    recs, _total = await dataset_service.list_dataset_records_admin(
        db, slug=slug, prefix=prefix, limit=limit, offset=offset
    )
    return [DatasetRecordAdminOut.from_record(r) for r in recs]


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    slug: Slug,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    await dataset_service.delete_dataset(db, slug)
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.DATASET_DELETE,
        resource_type="dataset",
        resource_id=slug,
        payload={"slug": slug},
        ip=ip,
        user_agent=ua,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{slug}/record", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset_record(
    slug: Slug,
    key: Annotated[str, Query(min_length=1, max_length=200)],
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    await dataset_service.delete_record_admin(db, slug=slug, record_key=key)
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.DATASET_RECORD_DELETE,
        resource_type="dataset",
        resource_id=slug,
        payload={"slug": slug, "key": key},
        ip=ip,
        user_agent=ua,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
