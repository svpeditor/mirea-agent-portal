"""Pydantic-схемы invite-эндпоинтов."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class InviteCreateIn(BaseModel):
    email: EmailStr
    role: Literal["user", "admin"] = "user"

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token: str
    email: str
    created_by_user_id: uuid.UUID
    expires_at: datetime
    used_at: datetime | None
    used_by_user_id: uuid.UUID | None
    created_at: datetime
    role: str = "user"
    registration_url: str | None = None


class InviteCreateOut(BaseModel):
    id: uuid.UUID
    token: str
    email: str
    role: str
    expires_at: datetime
    registration_url: str


class InvitesListOut(BaseModel):
    invites: list[InviteOut]


InviteStatusFilter = Literal["active", "used", "expired", "all"]
