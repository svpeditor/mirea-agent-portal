# ruff: noqa: B008
"""FastAPI dependencies."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import jwt
from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.core.exceptions import Forbidden, NotAuthenticated
from portal_api.core.security import decode_token
from portal_api.db import get_db as _get_db
from portal_api.models import User
from portal_api.services.build_enqueue import BuildEnqueuer
from portal_api.services.job_enqueue import JobEnqueuer


# Реэкспорт под именем без префикса — чтобы override в тестах был один-в-один
async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in _get_db():
        yield session


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not access_token:
        raise NotAuthenticated()
    try:
        payload = decode_token(access_token)
    except jwt.InvalidTokenError as e:
        raise NotAuthenticated() from e

    if payload.get("typ") != "access":
        raise NotAuthenticated()

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise NotAuthenticated() from e

    user = await db.get(User, user_id)
    if user is None:
        raise NotAuthenticated()
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise Forbidden()
    return user


def get_build_enqueuer(settings: Settings = Depends(get_settings)) -> BuildEnqueuer:
    return BuildEnqueuer(str(settings.redis_url))


def get_job_enqueuer(
    settings: Settings = Depends(get_settings),
) -> JobEnqueuer:
    return JobEnqueuer(redis_url=str(settings.redis_url))
