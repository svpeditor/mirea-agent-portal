"""Smoke-тест: /api/health отвечает."""
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
