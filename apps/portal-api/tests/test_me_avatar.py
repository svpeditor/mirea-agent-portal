"""Тесты для /api/me/avatar — upload / fetch / delete."""
from __future__ import annotations

import copy
import io
import struct
import zlib

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import User


def _make_settings_override(tmp_path):
    from portal_api.config import get_settings
    base = get_settings()
    s = copy.copy(base)
    object.__setattr__(s, "file_store_local_root", tmp_path)
    return lambda: s


def _tiny_png() -> bytes:
    """Валидный PNG 1×1 пиксель — минимум для теста content-type+round-trip."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00", 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.mark.asyncio
async def test_upload_avatar_sets_has_avatar(
    user_client: AsyncClient, regular_user: User, tmp_path,
) -> None:
    from portal_api.config import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        png = _tiny_png()
        r = await user_client.post(
            "/api/me/avatar",
            files={"file": ("av.png", io.BytesIO(png), "image/png")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["has_avatar"] is True
        assert body["avatar_version"] is not None
        assert len(body["avatar_version"]) == 8  # короткий cache-buster

        # Round-trip: GET возвращает те же байты
        g = await user_client.get("/api/me/avatar")
        assert g.status_code == 200
        assert g.headers["content-type"] == "image/png"
        assert g.content == png
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_upload_avatar_rejects_bad_content_type(
    user_client: AsyncClient, tmp_path,
) -> None:
    from portal_api.config import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        r = await user_client.post(
            "/api/me/avatar",
            files={"file": ("evil.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "AVATAR_BAD_TYPE"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_upload_avatar_rejects_oversize(
    user_client: AsyncClient, tmp_path,
) -> None:
    from portal_api.config import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        # 3MB > лимита 2MB
        big = b"\x00" * (3 * 1024 * 1024)
        r = await user_client.post(
            "/api/me/avatar",
            files={"file": ("big.png", io.BytesIO(big), "image/png")},
        )
        assert r.status_code == 413
        assert r.json()["detail"]["error"]["code"] == "AVATAR_TOO_LARGE"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_get_avatar_404_when_not_set(user_client: AsyncClient) -> None:
    r = await user_client.get("/api/me/avatar")
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "AVATAR_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_avatar_resets_fields(
    user_client: AsyncClient, regular_user: User, db: AsyncSession, tmp_path,
) -> None:
    from portal_api.config import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        # сначала загрузить
        await user_client.post(
            "/api/me/avatar",
            files={"file": ("av.png", io.BytesIO(_tiny_png()), "image/png")},
        )
        # потом удалить
        d = await user_client.delete("/api/me/avatar")
        assert d.status_code == 200
        assert d.json()["has_avatar"] is False
        assert d.json()["avatar_version"] is None

        # GET → 404
        g = await user_client.get("/api/me/avatar")
        assert g.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_avatar_requires_auth(client: AsyncClient, tmp_path) -> None:
    r = await client.post(
        "/api/me/avatar",
        files={"file": ("av.png", io.BytesIO(_tiny_png()), "image/png")},
    )
    # 401 (нет cookie) — но Origin middleware пропускает POST с Origin: http://test,
    # так что проверяем именно отсутствие auth.
    assert r.status_code in (401, 403)
