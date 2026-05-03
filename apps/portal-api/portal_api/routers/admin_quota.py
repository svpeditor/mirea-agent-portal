# ruff: noqa: B008
"""Admin endpoints для управления квотами и просмотра агрегированного usage."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import UserNotFound
from portal_api.deps import get_db, require_admin
from portal_api.models import Agent, UsageLog, User, UserQuota
from portal_api.schemas.llm import (
    AdminUsageByAgentSchema,
    AdminUsageByModelSchema,
    AdminUsageByUserSchema,
    AdminUsageSummarySchema,
    QuotaPatchSchema,
    UserQuotaSchema,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-quota"],
    dependencies=[Depends(require_admin)],
)


async def _get_quota_or_404(db: AsyncSession, user_id: uuid.UUID) -> UserQuota:
    """Вернуть UserQuota или UserNotFound."""
    quota = await db.get(UserQuota, user_id)
    if quota is None:
        raise UserNotFound()
    return quota


@router.patch("/users/{user_id}/quota", response_model=UserQuotaSchema)
async def patch_quota(
    user_id: uuid.UUID,
    payload: QuotaPatchSchema,
    db: AsyncSession = Depends(get_db),
) -> UserQuota:
    quota = await _get_quota_or_404(db, user_id)
    if payload.monthly_limit_usd is not None:
        quota.monthly_limit_usd = payload.monthly_limit_usd
    if payload.per_job_cap_usd is not None:
        quota.per_job_cap_usd = payload.per_job_cap_usd
    quota.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(quota)
    return quota


@router.post("/users/{user_id}/quota/reset", response_model=UserQuotaSchema)
async def reset_quota(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UserQuota:
    quota = await _get_quota_or_404(db, user_id)
    quota.period_used_usd = sa.text("0.0000")  # type: ignore[assignment]
    quota.period_used_usd = 0  # type: ignore[assignment]
    quota.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(quota)
    return quota


@router.get("/usage", response_model=AdminUsageSummarySchema)
async def get_usage_summary(
    agent_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminUsageSummarySchema:
    """Агрегированный usage по всей системе (или по одному агенту)."""
    base_filter = []
    if agent_id is not None:
        base_filter.append(UsageLog.agent_id == agent_id)

    # --- totals ---
    totals_stmt = sa.select(
        sa.func.count(UsageLog.id).label("total_requests"),
        sa.func.coalesce(sa.func.sum(UsageLog.cost_usd), 0).label("total_cost_usd"),
    ).where(*base_filter)
    totals_row = (await db.execute(totals_stmt)).one()
    total_requests: int = totals_row.total_requests
    total_cost_usd = totals_row.total_cost_usd

    # --- by_user ---
    by_user_stmt = (
        sa.select(
            UsageLog.user_id,
            User.email,
            sa.func.count(UsageLog.id).label("requests"),
            sa.func.sum(UsageLog.cost_usd).label("cost_usd"),
        )
        .join(User, UsageLog.user_id == User.id)
        .where(*base_filter)
        .group_by(UsageLog.user_id, User.email)
        .order_by(sa.desc("cost_usd"))
    )
    by_user_rows = (await db.execute(by_user_stmt)).all()
    by_user = [
        AdminUsageByUserSchema(
            user_id=row.user_id,
            email=row.email,
            requests=row.requests,
            cost_usd=row.cost_usd,
        )
        for row in by_user_rows
    ]

    # --- by_agent ---
    by_agent_stmt = (
        sa.select(
            UsageLog.agent_id,
            Agent.slug,
            sa.func.count(UsageLog.id).label("requests"),
            sa.func.sum(UsageLog.cost_usd).label("cost_usd"),
        )
        .join(Agent, UsageLog.agent_id == Agent.id)
        .where(*base_filter)
        .group_by(UsageLog.agent_id, Agent.slug)
        .order_by(sa.desc("cost_usd"))
    )
    by_agent_rows = (await db.execute(by_agent_stmt)).all()
    by_agent = [
        AdminUsageByAgentSchema(
            agent_id=row.agent_id,
            slug=row.slug,
            requests=row.requests,
            cost_usd=row.cost_usd,
        )
        for row in by_agent_rows
    ]

    # --- by_model ---
    by_model_stmt = (
        sa.select(
            UsageLog.model,
            sa.func.count(UsageLog.id).label("requests"),
            sa.func.sum(UsageLog.cost_usd).label("cost_usd"),
        )
        .where(*base_filter)
        .group_by(UsageLog.model)
        .order_by(sa.desc("cost_usd"))
    )
    by_model_rows = (await db.execute(by_model_stmt)).all()
    by_model = [
        AdminUsageByModelSchema(
            model=row.model,
            requests=row.requests,
            cost_usd=row.cost_usd,
        )
        for row in by_model_rows
    ]

    return AdminUsageSummarySchema(
        total_cost_usd=total_cost_usd,
        total_requests=total_requests,
        by_user=by_user,
        by_agent=by_agent,
        by_model=by_model,
    )
