"""FastAPI dependency для Bearer ephemeral-token auth (LLM-прокси)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import InvalidEphemeralTokenError
from portal_api.db import get_db
from portal_api.services.ephemeral_token import (
    EphemeralTokenContext, resolve,
)


async def ephemeral_token_auth(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> EphemeralTokenContext:
    """Bearer auth для /llm/v1/* эндпоинтов."""
    if authorization is None:
        raise InvalidEphemeralTokenError("missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidEphemeralTokenError("expected 'Bearer <token>' scheme")

    ctx = await resolve(db, token.strip())
    if ctx is None:
        raise InvalidEphemeralTokenError("token not found, expired, or revoked")
    return ctx
