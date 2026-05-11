"""DTO для agents."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class AgentTabBrief(BaseModel):
    slug: str
    name: str


class AgentCurrentVersionBrief(BaseModel):
    id: uuid.UUID
    manifest_version: str
    git_sha: str


class AgentLatestVersionAdminBrief(BaseModel):
    id: uuid.UUID
    status: str
    git_sha: str
    created_at: datetime


class AgentPublicOut(BaseModel):
    """Что видит юзер в `GET /api/agents`."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    short_description: str
    tab: AgentTabBrief
    current_version: AgentCurrentVersionBrief


class AgentDetailOut(AgentPublicOut):
    """`GET /api/agents/{slug}` — добавляет manifest полностью."""
    manifest: dict[str, Any]


class AgentAdminOut(BaseModel):
    """Что видит админ в `GET /api/admin/agents`."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    short_description: str
    tab_id: uuid.UUID
    current_version_id: uuid.UUID | None
    enabled: bool
    git_url: str
    cost_cap_usd: Decimal | None = None
    created_at: datetime
    updated_at: datetime
    latest_version: AgentLatestVersionAdminBrief | None = None


class AgentCreateIn(BaseModel):
    git_url: AnyUrl
    git_ref: str = Field(default="main", min_length=1, max_length=200)


class AgentUpdateIn(BaseModel):
    tab_id: uuid.UUID | None = None
    enabled: bool | None = None
    cost_cap_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
