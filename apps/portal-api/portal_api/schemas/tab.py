"""DTO для tabs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    order_idx: int


class TabAdminOut(TabOut):
    is_system: bool
    created_at: datetime
    updated_at: datetime


class TabCreateIn(BaseModel):
    slug: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9а-я-]+$",  # noqa: RUF001
    )
    name: str = Field(min_length=1, max_length=128)
    icon: str | None = Field(default=None, max_length=64)
    order_idx: int = 0


class TabUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    icon: str | None = Field(default=None, max_length=64)
    order_idx: int | None = None
