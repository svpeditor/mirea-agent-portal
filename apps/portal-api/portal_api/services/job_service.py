"""Бизнес-логика jobs."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import AgentNotFoundError, AgentNotReadyError
from portal_api.models import Agent, AgentVersion, Job, User


async def create_job(
    session: AsyncSession,
    *,
    agent_slug: str,
    params: dict[str, Any],
    user_id: uuid.UUID,
) -> Job:
    """Создать job; raises AgentNotFoundError / AgentNotReadyError."""
    stmt = (
        select(Agent, AgentVersion)
        .join(AgentVersion, AgentVersion.id == Agent.current_version_id)
        .where(Agent.slug == agent_slug, Agent.enabled.is_(True))
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise AgentNotFoundError()
    _agent, version = row
    if version.status != "ready":
        raise AgentNotReadyError()

    job = Job(
        id=uuid.uuid4(),
        agent_version_id=version.id,
        created_by_user_id=user_id,
        status="queued",
        params_jsonb=params,
    )
    session.add(job)
    await session.flush()
    return job


async def get_job_for_user(
    session: AsyncSession, job_id: uuid.UUID, user: User,
) -> Job | None:
    """Owner или admin видит. Иначе None (то же что 404 наружу)."""
    job = (
        await session.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()
    if job is None:
        return None
    if user.role == "admin" or job.created_by_user_id == user.id:
        return job
    return None


async def list_for_user(
    session: AsyncSession,
    user: User,
    *,
    limit: int = 20,
    before: uuid.UUID | None = None,
) -> list[Job]:
    """Cursor pagination — (created_at DESC, id DESC), before=id предыдущей страницы."""
    stmt = select(Job).where(Job.created_by_user_id == user.id)
    if before is not None:
        before_job = (
            await session.execute(select(Job).where(Job.id == before))
        ).scalar_one_or_none()
        if before_job is not None:
            # Композитный keyset (created_at, id): два job могут оказаться в одной микросекунде
            # (тесты создают 5 jobs in a row); без id-разрешителя страница теряет/дублирует строки.
            stmt = stmt.where(
                or_(
                    Job.created_at < before_job.created_at,
                    and_(Job.created_at == before_job.created_at, Job.id < before_job.id),
                )
            )
    stmt = stmt.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def cancel_job(
    session: AsyncSession, job_id: uuid.UUID, user: User,
) -> Job | None:
    """Атомарно cancel queued. Если running — пометить флаг (worker увидит).

    Возвращает обновлённый Job, либо None если 404 (нет / чужой).
    raises JobAlreadyFinishedError если в финальном статусе.
    """
    from portal_api.core.exceptions import JobAlreadyFinishedError

    job = await get_job_for_user(session, job_id, user)
    if job is None:
        return None
    if job.status in ("ready", "failed"):
        raise JobAlreadyFinishedError()
    if job.status == "cancelled":
        return job  # idempotent
    if job.status == "queued":
        result = await session.execute(text("""
            UPDATE jobs SET status='cancelled', finished_at=:now
            WHERE id=:vid AND status='queued'
            RETURNING id
        """), {"vid": job_id, "now": datetime.now(UTC)})
        if result.first() is None:
            await session.refresh(job)
            if job.status == "running":
                return job
            raise JobAlreadyFinishedError()
        await session.commit()
        await session.refresh(job)
        return job
    return job
