# ruff: noqa: B008, RUF002
"""Sandbox dataset endpoints — общая база данных для агентов.

Агент (в песочнице, ephemeral-токен) пишет и читает записи общей базы. Права
(read/write) берутся из манифеста его версии. Один агент наполняет, другие
читают — кросс-агентный обмен данными внутри портала.
"""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.llm_auth import ephemeral_token_auth
from portal_api.deps import get_db
from portal_api.schemas.dataset import (
    DatasetRecordIn,
    DatasetRecordListOut,
    DatasetRecordOut,
)
from portal_api.services import dataset_service
from portal_api.services.ephemeral_token import EphemeralTokenContext

router = APIRouter(prefix="/api/sandbox/datasets", tags=["sandbox-datasets"])

_log = structlog.get_logger()

Slug = Annotated[
    str, Path(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=80)
]


@router.put("/{slug}/record", response_model=DatasetRecordOut)
async def put_record(
    slug: Slug,
    payload: DatasetRecordIn,
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
) -> DatasetRecordOut:
    """Записать/обновить запись по ключу (требуется write/readwrite)."""
    rec, created = await dataset_service.put_record(
        db,
        agent_id=ctx.agent_id,
        agent_version_id=ctx.agent_version_id,
        job_id=ctx.job_id,
        slug=slug,
        record_key=payload.key,
        content_format=payload.content_format,
        value=payload.value,
        content=payload.content,
    )
    _log.info(
        "dataset_write", slug=slug, key=payload.key,
        created=created, agent_id=str(ctx.agent_id), job_id=str(ctx.job_id),
    )
    return DatasetRecordOut.from_record(rec)


@router.get("/{slug}/record", response_model=DatasetRecordOut)
async def get_record(
    slug: Slug,
    key: Annotated[str, Query(min_length=1, max_length=200)],
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
) -> DatasetRecordOut:
    """Прочитать запись по ключу (требуется read/readwrite)."""
    rec = await dataset_service.get_record(
        db, agent_version_id=ctx.agent_version_id, slug=slug, record_key=key
    )
    return DatasetRecordOut.from_record(rec)


@router.get("/{slug}/records", response_model=DatasetRecordListOut)
async def list_records(
    slug: Slug,
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
    prefix: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=dataset_service.MAX_LIST_LIMIT)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DatasetRecordListOut:
    """Список записей датасета (требуется read/readwrite)."""
    recs, total = await dataset_service.list_records(
        db, agent_version_id=ctx.agent_version_id, slug=slug,
        prefix=prefix, limit=limit, offset=offset,
    )
    return DatasetRecordListOut(
        items=[DatasetRecordOut.from_record(r) for r in recs],
        total=total, limit=limit, offset=offset,
    )


@router.delete("/{slug}/record", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    slug: Slug,
    key: Annotated[str, Query(min_length=1, max_length=200)],
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Удалить запись по ключу (требуется write/readwrite)."""
    await dataset_service.delete_record(
        db, agent_version_id=ctx.agent_version_id, slug=slug, record_key=key
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
