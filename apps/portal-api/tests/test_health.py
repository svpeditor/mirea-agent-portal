"""Smoke-тесты: /api/health и /api/health/full."""
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    from portal_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def _override_redis(redis_url: str):
    """Подменить settings.redis_url на адрес тестового Redis-контейнера.
    Возвращает callable для cleanup."""
    from portal_api.config import get_settings as cfg_get_settings
    from portal_api.deps import get_settings as deps_get_settings
    from portal_api.main import app

    base = cfg_get_settings()
    object.__setattr__(base, "redis_url", redis_url)
    app.dependency_overrides[deps_get_settings] = lambda: base

    def cleanup() -> None:
        app.dependency_overrides.pop(deps_get_settings, None)

    return cleanup


@pytest.mark.asyncio
async def test_health_full_ok_when_dependencies_alive(user_client, redis_url) -> None:
    """Если postgres+redis подняты — /health/full отдаёт ok."""
    cleanup = _override_redis(redis_url)
    try:
        resp = await user_client.get("/api/health/full")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "ok"
        assert body["checks"]["postgres"] == "ok"
        assert body["checks"]["redis"] == "ok"
        assert "uptime_seconds" in body
        assert "environment" in body
    finally:
        cleanup()


@pytest.mark.asyncio
async def test_health_full_503_on_redis_down(user_client) -> None:
    """Если REDIS_URL ломаный — /health/full возвращает 503."""
    # фейк-урл с портом, к которому невозможно подключиться
    cleanup = _override_redis("redis://127.0.0.1:1/0")
    try:
        resp = await user_client.get("/api/health/full")
        assert resp.status_code == 503
        body = resp.json()
        # FastAPI оборачивает HTTPException.detail в {"detail": ...}
        assert body["detail"]["status"] == "degraded"
        assert body["detail"]["checks"]["postgres"] == "ok"
        assert body["detail"]["checks"]["redis"].startswith("error:")
    finally:
        cleanup()
