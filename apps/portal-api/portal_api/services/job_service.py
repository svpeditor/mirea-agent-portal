"""Бизнес-логика jobs."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import AgentNotFoundError, AgentNotReadyError, QuotaExhaustedError
from portal_api.models import Agent, AgentVersion, Job, User, UserQuota
from portal_api.schemas.job import JobListItemOut
from portal_api.services import ephemeral_token as eph_svc


async def create_job(
    session: AsyncSession,
    *,
    agent_slug: str,
    params: dict[str, Any],
    user_id: uuid.UUID,
) -> tuple[Job, str | None]:
    """Создать job; raises AgentNotFoundError / AgentNotReadyError / QuotaExhaustedError.

    Returns (job, ephemeral_plaintext) — ephemeral_plaintext is None if agent has no runtime.llm.
    """
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

    manifest = version.manifest_jsonb or {}
    runtime_llm = (manifest.get("runtime") or {}).get("llm")
    ephemeral_plaintext: str | None = None

    if runtime_llm:
        quota = await session.get(UserQuota, user_id)
        if quota and quota.period_used_usd >= quota.monthly_limit_usd:
            raise QuotaExhaustedError(
                f"monthly limit ${quota.monthly_limit_usd} exceeded "
                f"(used ${quota.period_used_usd})"
            )

    job = Job(
        id=uuid.uuid4(),
        agent_version_id=version.id,
        created_by_user_id=user_id,
        status="queued",
        params_jsonb=params,
    )
    session.add(job)
    await session.flush()

    if runtime_llm:
        max_runtime = (manifest.get("runtime") or {}).get("limits", {}).get("max_runtime_minutes", 60)
        ttl = timedelta(minutes=int(max_runtime) + 5)
        ephemeral_plaintext, _ = eph_svc.generate()
        await eph_svc.insert(
            session,
            plaintext=ephemeral_plaintext,
            job_id=job.id,
            user_id=user_id,
            agent_version_id=version.id,
            ttl=ttl,
        )

    return job, ephemeral_plaintext


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
) -> list[JobListItemOut]:
    """Cursor pagination — (created_at DESC, id DESC), before=id предыдущей страницы.

    Возвращает enriched DTO с agent_slug/agent_name через join на
    agent_versions/agents (frontend JobsTable рендерит их вместо UUID).
    """
    stmt = (
        select(
            Job.id,
            Job.status,
            Job.agent_version_id,
            Agent.slug.label("agent_slug"),
            Agent.name.label("agent_name"),
            Job.cost_usd_total,
            Job.created_at,
            Job.started_at,
            Job.finished_at,
            Job.error_code,
        )
        .join(AgentVersion, AgentVersion.id == Job.agent_version_id)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .where(Job.created_by_user_id == user.id)
    )
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
    rows = (await session.execute(stmt)).all()
    return [JobListItemOut.model_validate(row, from_attributes=True) for row in rows]


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
