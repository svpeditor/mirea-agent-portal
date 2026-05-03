"""Запросы к job_events."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import JobEvent


async def list_since(
    session: AsyncSession,
    job_id: uuid.UUID,
    *,
    since: int = 0,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return events with seq > since, ordered by seq ASC, up to limit."""
    stmt = (
        select(JobEvent)
        .where(JobEvent.job_id == job_id, JobEvent.seq > since)
        .order_by(JobEvent.seq)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "seq": e.seq,
            "ts": e.ts.isoformat(),
            "type": e.event_type,
            "payload": e.payload_jsonb,
        }
        for e in rows
    ]


async def count_for_job(session: AsyncSession, job_id: uuid.UUID) -> tuple[int, int | None]:
    """(count, max_seq | None)."""
    row = (await session.execute(
        select(func.count(JobEvent.id), func.max(JobEvent.seq))
        .where(JobEvent.job_id == job_id)
    )).one()
    return int(row[0]), row[1]
