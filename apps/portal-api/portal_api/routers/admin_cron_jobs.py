# ruff: noqa: B008
"""Admin endpoints для cron_jobs: CRUD."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.deps import get_db, require_admin
from portal_api.models import Agent, CronJob, User
from portal_api.schemas.cron_job import (
    CronJobAdminOut,
    CronJobCreateIn,
    CronJobUpdateIn,
)
from portal_api.services.cron_schedule import next_run_after, utc_now

router = APIRouter(
    prefix="/admin/cron_jobs", tags=["admin-cron"],
    dependencies=[Depends(require_admin)],
)


def _to_admin_out(cj: CronJob, agent: Agent, creator_email: str) -> CronJobAdminOut:
    return CronJobAdminOut(
        id=cj.id,
        agent_id=cj.agent_id,
        schedule=cj.schedule,  # type: ignore[arg-type]
        params=cj.params_jsonb,
        enabled=cj.enabled,
        last_run_at=cj.last_run_at,
        next_run_at=cj.next_run_at,
        last_job_id=cj.last_job_id,
        created_at=cj.created_at,
        agent_slug=agent.slug,
        agent_name=agent.name,
        created_by_email=creator_email,
    )


@router.get("", response_model=list[CronJobAdminOut])
async def list_cron_jobs(db: AsyncSession = Depends(get_db)) -> list[CronJobAdminOut]:
    rows = (
        await db.execute(
            sa.select(CronJob, Agent, User.email)
            .join(Agent, Agent.id == CronJob.agent_id)
            .join(User, User.id == CronJob.created_by_user_id)
            .order_by(CronJob.created_at.desc())
        )
    ).all()
    return [_to_admin_out(cj, ag, email) for cj, ag, email in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CronJobAdminOut)
async def create_cron_job(
    payload: CronJobCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> CronJobAdminOut:
    agent = await db.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "AGENT_NOT_FOUND"}})
    if agent.current_version_id is None:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "NO_CURRENT_VERSION", "message": "у агента нет current_version"}},
        )

    now = utc_now()
    cj = CronJob(
        agent_id=payload.agent_id,
        schedule=payload.schedule,
        params_jsonb=payload.params,
        created_by_user_id=admin.id,
        enabled=True,
        next_run_at=next_run_after(now, payload.schedule),
    )
    db.add(cj)
    await db.flush()
    await db.commit()
    await db.refresh(cj)
    return _to_admin_out(cj, agent, admin.email)


@router.patch("/{cron_id}", response_model=CronJobAdminOut)
async def update_cron_job(
    cron_id: uuid.UUID,
    payload: CronJobUpdateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),  # noqa: ARG001
) -> CronJobAdminOut:
    cj = await db.get(CronJob, cron_id)
    if cj is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "CRON_NOT_FOUND"}})
    if payload.enabled is not None:
        cj.enabled = payload.enabled
    if payload.schedule is not None and payload.schedule != cj.schedule:
        cj.schedule = payload.schedule
        cj.next_run_at = next_run_after(utc_now(), payload.schedule)
    if payload.params is not None:
        cj.params_jsonb = payload.params
    await db.flush()
    await db.commit()
    await db.refresh(cj)
    agent = await db.get(Agent, cj.agent_id)
    creator = await db.get(User, cj.created_by_user_id)
    return _to_admin_out(cj, agent, creator.email if creator else "?")


@router.delete("/{cron_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cron_job(
    cron_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    cj = await db.get(CronJob, cron_id)
    if cj is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "CRON_NOT_FOUND"}})
    await db.delete(cj)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
