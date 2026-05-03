"""DTO для jobs.

JobListItemOut и JobFileOut поддерживают `model_validate(orm)` через
`from_attributes=True`. Остальные DTO (JobCreatedOut, JobDetailOut,
JobEventOut) собираются в service layer вручную из-за переименования полей
(event_type→type, payload_jsonb→payload, params_jsonb→params,
output_summary_jsonb→output_summary) или service-computed полей
(agent_slug, events_count, last_event_seq, agent).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobCreatedOut(BaseModel):
    """Ответ POST /api/agents/{slug}/jobs. agent_slug → join, не from_attributes."""

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
    """Ответ GET /api/jobs/{id}.

    params/output_summary переименованы; events_count/last_event_seq/agent — отдельные queries.
    """

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
    """Один event для GET /api/jobs/{id}/events и WS stream.

    type/payload — переименования, конструировать вручную.
    """

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
