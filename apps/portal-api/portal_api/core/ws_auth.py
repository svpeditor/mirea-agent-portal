# ruff: noqa: RUF002
"""Auth-helper для WebSocket: достаёт юзера из cookie."""
from __future__ import annotations

import uuid

import jwt
from fastapi import WebSocket, WebSocketException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.security import decode_token
from portal_api.models import User

_4401 = 4401  # custom WS close code: unauthenticated


async def get_current_user_ws(websocket: WebSocket, session: AsyncSession) -> User:
    """Извлечь юзера из access cookie. Иначе закрыть с кодом 4401."""
    cookies = websocket.cookies
    token = cookies.get("access_token")
    if not token:
        raise WebSocketException(code=_4401, reason="no_auth")
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        raise WebSocketException(code=_4401, reason="invalid_token") from None
    except Exception:
        raise WebSocketException(code=_4401, reason="invalid_token") from None

    if payload.get("typ") != "access":
        raise WebSocketException(code=_4401, reason="not_access_token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise WebSocketException(code=_4401, reason="invalid_sub") from None

    user = (await session.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    if user is None:
        raise WebSocketException(code=_4401, reason="user_not_found")
    return user
