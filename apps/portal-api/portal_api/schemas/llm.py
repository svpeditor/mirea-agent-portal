"""Pydantic schemas для LLM-прокси (quota, usage, admin)."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class UserQuotaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    monthly_limit_usd: Decimal
    period_used_usd: Decimal
    period_starts_at: datetime
    per_job_cap_usd: Decimal


class UsageLogItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    agent_slug: str | None = None
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    status: str
    created_at: datetime


class UsagePageSchema(BaseModel):
    items: list[UsageLogItemSchema]
    next_cursor: str | None


class QuotaPatchSchema(BaseModel):
    monthly_limit_usd: Decimal | None = None
    per_job_cap_usd: Decimal | None = None


class AdminUsageBucketSchema(BaseModel):
    cost_usd: Decimal
    requests: int


class AdminUsageByUserSchema(AdminUsageBucketSchema):
    user_id: uuid.UUID
    email: str


class AdminUsageByAgentSchema(AdminUsageBucketSchema):
    agent_id: uuid.UUID
    slug: str


class AdminUsageByModelSchema(AdminUsageBucketSchema):
    model: str


class AdminUsageSummarySchema(BaseModel):
    total_cost_usd: Decimal
    total_requests: int
    by_user: list[AdminUsageByUserSchema]
    by_agent: list[AdminUsageByAgentSchema]
    by_model: list[AdminUsageByModelSchema]
