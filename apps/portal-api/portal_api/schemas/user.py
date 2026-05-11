"""Pydantic-схемы юзера."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from portal_api.schemas.llm import UserQuotaSchema


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: str
    monthly_budget_usd: Decimal
    has_avatar: bool = False
    avatar_version: str | None = None
    created_at: datetime


class UserAdminOut(UserOut):
    """Расширенный UserOut для admin-эндпоинтов — включает quota."""

    quota: UserQuotaSchema | None = None


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class UserAdminUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None)
    monthly_budget_usd: Decimal | None = Field(default=None, ge=0)

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return v


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordOut(BaseModel):
    temporary_password: str
