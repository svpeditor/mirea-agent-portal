"""Бизнес-логика общей базы данных агентов (datasets).

Агент обращается к датасету через sandbox-эндпоинт с ephemeral-токеном. Токен
даёт `agent_version_id`; права (read/write) берём из манифеста этой версии
(`runtime.datasets`). Писать/читать можно ТОЛЬКО объявленные там датасеты.
Датасет создаётся лениво при первой записи.
"""
# ruff: noqa: RUF001, RUF002, RUF003
from __future__ import annotations

import json
import uuid
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import (
    DatasetAccessDeniedError,
    DatasetFullError,
    DatasetNotFoundError,
    DatasetRecordNotFoundError,
    DatasetRecordTooLargeError,
)
from portal_api.models import AgentVersion, Dataset, DatasetRecord

# Лимиты (soft caps). Размер = utf-8 байты content_text + JSON-сериализация value.
MAX_RECORD_BYTES = 256 * 1024
MAX_RECORDS_PER_DATASET = 50_000
MAX_LIST_LIMIT = 200
# Допустимые форматы валидирует схема (Literal в DatasetRecordIn); здесь — справочно.
ALLOWED_FORMATS = ("json", "latex", "text")

Access = Literal["read", "write", "readwrite"]


def _like_prefix(prefix: str) -> str:
    """Экранировать спец-символы LIKE (\\, %, _) для безопасного startswith."""
    escaped = prefix.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return escaped + "%"


def _record_size_bytes(value: dict[str, Any] | None, content: str | None) -> int:
    size = 0
    if content is not None:
        size += len(content.encode("utf-8"))
    if value is not None:
        size += len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    return size


async def _grants_for_version(
    session: AsyncSession, agent_version_id: uuid.UUID
) -> dict[str, str]:
    """slug -> access из manifest_jsonb.runtime.datasets версии агента."""
    manifest = (
        await session.execute(
            sa.select(AgentVersion.manifest_jsonb).where(
                AgentVersion.id == agent_version_id
            )
        )
    ).scalar_one_or_none() or {}
    raw = ((manifest.get("runtime") or {}).get("datasets")) or []
    grants: dict[str, str] = {}
    for g in raw:
        if isinstance(g, dict) and "slug" in g:
            grants[str(g["slug"])] = str(g.get("access", "read"))
    return grants


async def _require_access(
    session: AsyncSession,
    *,
    agent_version_id: uuid.UUID,
    slug: str,
    need: Literal["read", "write"],
) -> None:
    grants = await _grants_for_version(session, agent_version_id)
    access = grants.get(slug)
    if access is None:
        raise DatasetAccessDeniedError(
            f"Датасет '{slug}' не объявлен в манифесте агента (runtime.datasets)."
        )
    ok = access == "readwrite" or access == need
    if not ok:
        raise DatasetAccessDeniedError(
            f"У агента доступ '{access}' к датасету '{slug}', требуется '{need}'."
        )


async def _get_dataset_id(session: AsyncSession, slug: str) -> uuid.UUID | None:
    return (
        await session.execute(sa.select(Dataset.id).where(Dataset.slug == slug))
    ).scalar_one_or_none()


async def _get_or_create_dataset_id(session: AsyncSession, slug: str) -> uuid.UUID:
    """Лениво создаёт датасет. Race-safe через ON CONFLICT DO NOTHING.

    При гонке двух писателей по новому slug конкурирующий INSERT блокируется на
    незакоммиченной строке, а последующий SELECT под READ COMMITTED видит уже
    закоммиченную строку, поэтому assert ниже не срабатывает.
    """
    await session.execute(
        pg_insert(Dataset.__table__)
        .values(id=uuid.uuid4(), slug=slug)
        .on_conflict_do_nothing(index_elements=["slug"])
    )
    ds_id = await _get_dataset_id(session, slug)
    assert ds_id is not None
    return ds_id


async def put_record(
    session: AsyncSession,
    *,
    agent_id: uuid.UUID,
    agent_version_id: uuid.UUID,
    job_id: uuid.UUID,
    slug: str,
    record_key: str,
    content_format: str,
    value: dict[str, Any] | None,
    content: str | None,
) -> tuple[DatasetRecord, bool]:
    """Upsert записи. Возвращает (record, created) — created=True если новый ключ.

    content_format валидируется схемой (Literal), сюда приходит уже корректным.
    """
    size = _record_size_bytes(value, content)
    if size > MAX_RECORD_BYTES:
        raise DatasetRecordTooLargeError(
            f"Запись {size} Б превышает лимит {MAX_RECORD_BYTES} Б."
        )
    await _require_access(
        session, agent_version_id=agent_version_id, slug=slug, need="write"
    )
    dataset_id = await _get_or_create_dataset_id(session, slug)

    existing_id = (
        await session.execute(
            sa.select(DatasetRecord.id).where(
                DatasetRecord.dataset_id == dataset_id,
                DatasetRecord.record_key == record_key,
            )
        )
    ).scalar_one_or_none()
    is_new = existing_id is None
    if is_new:
        count = (
            await session.execute(
                sa.select(sa.func.count())
                .select_from(DatasetRecord)
                .where(DatasetRecord.dataset_id == dataset_id)
            )
        ).scalar_one()
        if count >= MAX_RECORDS_PER_DATASET:
            raise DatasetFullError(
                f"В датасете '{slug}' уже {count} записей (лимит {MAX_RECORDS_PER_DATASET})."
            )

    now = sa.func.now()
    stmt = (
        pg_insert(DatasetRecord.__table__)
        .values(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            record_key=record_key,
            content_format=content_format,
            value_jsonb=value,
            content_text=content,
            created_by_agent_id=agent_id,
            created_by_job_id=job_id,
        )
        .on_conflict_do_update(
            constraint="dataset_records_key_uq",
            # created_by_* НЕ трогаем на апдейте: колонки фиксируют первого
            # автора записи (created_at тоже сохраняется), меняется лишь
            # содержимое и updated_at.
            set_={
                "content_format": content_format,
                "value_jsonb": value,
                "content_text": content,
                "updated_at": now,
            },
        )
        .returning(DatasetRecord.__table__)
    )
    row = (await session.execute(stmt)).mappings().one()
    await session.commit()
    rec = DatasetRecord(**dict(row))
    return rec, is_new


async def get_record(
    session: AsyncSession,
    *,
    agent_version_id: uuid.UUID,
    slug: str,
    record_key: str,
) -> DatasetRecord:
    await _require_access(
        session, agent_version_id=agent_version_id, slug=slug, need="read"
    )
    dataset_id = await _get_dataset_id(session, slug)
    if dataset_id is None:
        raise DatasetRecordNotFoundError()
    rec = (
        await session.execute(
            sa.select(DatasetRecord).where(
                DatasetRecord.dataset_id == dataset_id,
                DatasetRecord.record_key == record_key,
            )
        )
    ).scalar_one_or_none()
    if rec is None:
        raise DatasetRecordNotFoundError()
    return rec


async def list_records(
    session: AsyncSession,
    *,
    agent_version_id: uuid.UUID,
    slug: str,
    prefix: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DatasetRecord], int]:
    """Вернуть (записи, total). Если датасета нет — ([], 0)."""
    await _require_access(
        session, agent_version_id=agent_version_id, slug=slug, need="read"
    )
    limit = max(1, min(limit, MAX_LIST_LIMIT))
    offset = max(0, offset)
    dataset_id = await _get_dataset_id(session, slug)
    if dataset_id is None:
        return [], 0

    where = [DatasetRecord.dataset_id == dataset_id]
    if prefix:
        where.append(DatasetRecord.record_key.like(_like_prefix(prefix), escape="\\"))
    total = (
        await session.execute(
            sa.select(sa.func.count()).select_from(DatasetRecord).where(*where)
        )
    ).scalar_one()
    rows = (
        await session.execute(
            sa.select(DatasetRecord)
            .where(*where)
            .order_by(DatasetRecord.created_at.asc(), DatasetRecord.id.asc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def delete_record(
    session: AsyncSession,
    *,
    agent_version_id: uuid.UUID,
    slug: str,
    record_key: str,
) -> None:
    await _require_access(
        session, agent_version_id=agent_version_id, slug=slug, need="write"
    )
    dataset_id = await _get_dataset_id(session, slug)
    if dataset_id is None:
        raise DatasetRecordNotFoundError()
    result = await session.execute(
        sa.delete(DatasetRecord).where(
            DatasetRecord.dataset_id == dataset_id,
            DatasetRecord.record_key == record_key,
        )
    )
    if result.rowcount == 0:
        raise DatasetRecordNotFoundError()
    await session.commit()


# --- Admin (без grant-проверок; вызывается только из admin-роутера) ---


async def list_datasets(session: AsyncSession) -> list[tuple[Dataset, int]]:
    """Все датасеты + число записей в каждом (для admin-обзора)."""
    count_sq = (
        sa.select(
            DatasetRecord.dataset_id,
            sa.func.count().label("cnt"),
        )
        .group_by(DatasetRecord.dataset_id)
        .subquery()
    )
    rows = (
        await session.execute(
            sa.select(Dataset, sa.func.coalesce(count_sq.c.cnt, 0))
            .outerjoin(count_sq, count_sq.c.dataset_id == Dataset.id)
            .order_by(Dataset.slug)
        )
    ).all()
    return [(ds, int(cnt)) for ds, cnt in rows]


async def get_dataset_by_slug(session: AsyncSession, slug: str) -> Dataset:
    ds = (
        await session.execute(sa.select(Dataset).where(Dataset.slug == slug))
    ).scalar_one_or_none()
    if ds is None:
        raise DatasetNotFoundError()
    return ds


async def list_dataset_records_admin(
    session: AsyncSession,
    *,
    slug: str,
    prefix: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DatasetRecord], int]:
    ds = await get_dataset_by_slug(session, slug)
    limit = max(1, min(limit, MAX_LIST_LIMIT))
    offset = max(0, offset)
    where = [DatasetRecord.dataset_id == ds.id]
    if prefix:
        where.append(DatasetRecord.record_key.like(_like_prefix(prefix), escape="\\"))
    total = (
        await session.execute(
            sa.select(sa.func.count()).select_from(DatasetRecord).where(*where)
        )
    ).scalar_one()
    rows = (
        await session.execute(
            sa.select(DatasetRecord)
            .where(*where)
            .order_by(DatasetRecord.created_at.asc(), DatasetRecord.id.asc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def delete_dataset(session: AsyncSession, slug: str) -> None:
    """Удалить датасет целиком (записи уходят каскадом)."""
    ds = await get_dataset_by_slug(session, slug)
    await session.delete(ds)
    await session.flush()


async def delete_record_admin(
    session: AsyncSession, *, slug: str, record_key: str
) -> None:
    ds = await get_dataset_by_slug(session, slug)
    result = await session.execute(
        sa.delete(DatasetRecord).where(
            DatasetRecord.dataset_id == ds.id,
            DatasetRecord.record_key == record_key,
        )
    )
    if result.rowcount == 0:
        raise DatasetRecordNotFoundError()
    await session.flush()
