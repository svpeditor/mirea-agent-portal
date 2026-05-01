"""Pydantic-схемы auth-эндпоинтов."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from portal_api.schemas.user import UserOut


class RegisterIn(BaseModel):
    token: str = Field(min_length=1)
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()


class AuthResponse(BaseModel):
    user: UserOut
