"""Unit-тесты на security.py — без БД."""
from __future__ import annotations

import os

import pytest

# Понизить bcrypt cost для скорости тестов
os.environ["BCRYPT_COST_TESTING"] = "4"


def test_hash_password_is_not_plaintext() -> None:
    from portal_api.core.security import hash_password, verify_password

    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h) is True


def test_verify_wrong_password_returns_false() -> None:
    from portal_api.core.security import hash_password, verify_password

    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_hash_password_is_non_deterministic() -> None:
    """Bcrypt с разной солью даёт разные хеши, но оба валидные."""
    from portal_api.core.security import hash_password, verify_password

    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2
    assert verify_password("same", h1) is True
    assert verify_password("same", h2) is True


def test_create_and_decode_access_token() -> None:
    from portal_api.core.security import create_access_token, decode_token

    token = create_access_token(user_id="11111111-1111-1111-1111-111111111111", role="user")
    payload = decode_token(token)
    assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
    assert payload["role"] == "user"
    assert payload["typ"] == "access"


def test_decode_invalid_token_raises() -> None:
    import jwt

    from portal_api.core.security import decode_token

    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not-a-jwt")


def test_decode_expired_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import jwt

    from portal_api.core.security import create_access_token, decode_token
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "-1")
    from portal_api.config import get_settings
    get_settings.cache_clear()

    token = create_access_token(user_id="aaaa", role="user")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
    get_settings.cache_clear()  # вернуть нормальное TTL


def test_generate_refresh_token_unique() -> None:
    from portal_api.core.security import generate_refresh_token

    a, _ = generate_refresh_token()
    b, _ = generate_refresh_token()
    assert a != b
    assert len(a) >= 40  # base64url(32 bytes) ≈ 43


def test_hash_refresh_token_deterministic() -> None:
    from portal_api.core.security import hash_refresh_token

    raw = "some-token"
    assert hash_refresh_token(raw) == hash_refresh_token(raw)
    assert hash_refresh_token(raw) != hash_refresh_token("different")


def test_generate_refresh_returns_matching_pair() -> None:
    from portal_api.core.security import generate_refresh_token, hash_refresh_token

    raw, h = generate_refresh_token()
    assert hash_refresh_token(raw) == h
