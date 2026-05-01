"""DTO для agent_versions."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentVersionListItemOut(BaseModel):
    """Элемент в `GET /api/admin/agents/{id}/versions`."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    git_ref: str
    git_sha: str
    manifest_version: str
    status: str
    build_started_at: datetime | None
    build_finished_at: datetime | None
    build_error: str | None
    is_current: bool


class AgentVersionDetailOut(BaseModel):
    """`GET /api/admin/agent_versions/{id}` — полная карточка."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    git_ref: str
    git_sha: str
    manifest_jsonb: dict[str, Any]
    manifest_version: str
    docker_image_tag: str | None
    status: str
    build_log: str | None
    build_started_at: datetime | None
    build_finished_at: datetime | None
    build_error: str | None
    is_current: bool
    created_at: datetime


class AgentVersionEnqueuedOut(BaseModel):
    """Что отдаём после POST /agents/{id}/versions или /agents (часть ответа)."""
    id: uuid.UUID
    status: str


class NewVersionIn(BaseModel):
    git_ref: str = Field(default="main", min_length=1, max_length=200)
