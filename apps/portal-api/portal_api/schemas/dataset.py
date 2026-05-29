"""DTO для общей базы данных агентов (datasets)."""
# ruff: noqa: RUF002
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatasetRecordIn(BaseModel):
    """Тело PUT /api/sandbox/datasets/{slug}/record."""

    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=200)
    content_format: Literal["json", "latex", "text"] = "json"
    value: dict[str, Any] | None = None
    content: str | None = None

    @model_validator(mode="after")
    def _need_payload(self) -> DatasetRecordIn:
        if self.value is None and self.content is None:
            raise ValueError("Нужно передать value (JSON) и/или content (текст).")
        return self


class DatasetRecordOut(BaseModel):
    """Запись, как её видит агент-читатель."""

    model_config = ConfigDict(from_attributes=True)
    key: str
    content_format: str
    value: dict[str, Any] | None = None
    content: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, rec: Any) -> DatasetRecordOut:
        return cls(
            key=rec.record_key,
            content_format=rec.content_format,
            value=rec.value_jsonb,
            content=rec.content_text,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )


class DatasetRecordListOut(BaseModel):
    items: list[DatasetRecordOut]
    total: int
    limit: int
    offset: int


# --- Admin DTO ---


class DatasetAdminOut(BaseModel):
    """Датасет в admin-обзоре (со счётчиком записей)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    description: str | None = None
    record_count: int
    created_at: datetime
    updated_at: datetime


class DatasetRecordAdminOut(BaseModel):
    """Запись для admin-просмотра (с автором и id)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    key: str
    content_format: str
    value: dict[str, Any] | None = None
    content: str | None = None
    created_by_agent_id: uuid.UUID | None = None
    created_by_job_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, rec: Any) -> DatasetRecordAdminOut:
        return cls(
            id=rec.id,
            key=rec.record_key,
            content_format=rec.content_format,
            value=rec.value_jsonb,
            content=rec.content_text,
            created_by_agent_id=rec.created_by_agent_id,
            created_by_job_id=rec.created_by_job_id,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
