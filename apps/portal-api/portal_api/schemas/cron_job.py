"""Pydantic-схемы для cron_jobs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SchedulePreset = Literal["hourly", "daily", "weekly", "monthly"]


class CronJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    schedule: SchedulePreset
    params_jsonb: dict[str, Any] = Field(alias="params")
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime
    last_job_id: uuid.UUID | None
    created_at: datetime


class CronJobAdminOut(CronJobOut):
    """С дополнительной инфой про агента — для админ-страниц."""
    agent_slug: str
    agent_name: str
    created_by_email: str


class CronJobCreateIn(BaseModel):
    agent_id: uuid.UUID
    schedule: SchedulePreset
    params: dict[str, Any] = Field(default_factory=dict)


class CronJobUpdateIn(BaseModel):
    enabled: bool | None = None
    schedule: SchedulePreset | None = None
    params: dict[str, Any] | None = None
