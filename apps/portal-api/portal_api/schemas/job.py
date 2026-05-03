"""DTO для jobs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobCreatedOut(BaseModel):
    id: uuid.UUID
    status: str
    agent_slug: str


class JobListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    agent_version_id: uuid.UUID
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None


class JobAgentBrief(BaseModel):
    slug: str
    name: str


class JobDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    agent_version_id: uuid.UUID
    agent: JobAgentBrief
    params: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    exit_code: int | None
    error_code: str | None
    error_msg: str | None
    output_summary: dict[str, Any] | None
    events_count: int
    last_event_seq: int | None
    created_at: datetime


class JobEventOut(BaseModel):
    seq: int
    ts: datetime
    type: str
    payload: dict[str, Any]


class JobFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    filename: str
    content_type: str | None
    size_bytes: int
    sha256: str
    created_at: datetime


class JobCancelOut(BaseModel):
    id: uuid.UUID
    status: str
