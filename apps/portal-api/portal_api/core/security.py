# ruff: noqa: RUF002
"""JWT, bcrypt, refresh-token utilities."""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from portal_api.config import get_settings


def _bcrypt_cost() -> int:
    """В тестах cost снижается до 4, в проде = 12."""
    raw = os.environ.get("BCRYPT_COST_TESTING")
    if raw:
        return int(raw)
    return 12


def hash_password(plain: str) -> str:
    """Bcrypt-хеш пароля. Вернёт строку с солью."""
    salt = bcrypt.gensalt(rounds=_bcrypt_cost())
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time проверка пароля."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, role: str) -> str:
    """JWT access-токен. Подпись HS256."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.jwt_access_ttl_seconds)).timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    # PyJWT 2.x returns str, but ряд stub-версий помечает Union[str, bytes] — нормализуем.
    if isinstance(encoded, bytes):
        return encoded.decode("utf-8")
    return encoded


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует JWT. Кидает jwt.InvalidTokenError при проблемах."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])


def generate_refresh_token() -> tuple[str, str]:
    """Генерит сырой refresh-токен и его SHA-256 хеш.

    Возвращает (raw, hash).
    raw — то, что отправляется юзеру в cookie.
    hash — то, что хранится в БД.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    """SHA-256 хеш refresh-токена для хранения в БД."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
