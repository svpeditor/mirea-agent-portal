"""GET /llm/v1/models возвращает manifest-whitelist агента в OpenAI-формате."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from portal_api.models import UserQuota
from portal_api.services import ephemeral_token as eph_svc
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


@pytest.mark.asyncio
async def test_get_models_returns_agent_whitelist(client, db, admin_user) -> None:
    from portal_api.db import get_db as _db_get_db
    from portal_api.main import app
    from portal_api.services.llm_pricing import PricingCache

    # Настроить pricing_cache в app.state (list_models его не использует, но lifespan требует)
    app.state.pricing_cache = PricingCache(base_url="https://openrouter.ai/api/v1", timeout_s=5.0)

    # Переопределить portal_api.db.get_db (используется в ephemeral_token_auth)
    async def _override_db():
        yield db

    app.dependency_overrides[_db_get_db] = _override_db

    user = await make_user(db, email="m@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-m", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-m", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
        manifest_jsonb={"runtime": {"llm": {"provider": "openrouter", "models": [
            "deepseek/deepseek-chat", "anthropic/claude-haiku-4-5",
        ]}}},
    )
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    plain, _ = eph_svc.generate()
    await eph_svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=user.id,
        agent_version_id=av.id, ttl=timedelta(minutes=65),
    )
    await db.flush()

    r = await client.get("/llm/v1/models", headers={"Authorization": f"Bearer {plain}"})
    assert r.status_code == 200
    data = r.json()
    assert data["object"] == "list"
    ids = [m["id"] for m in data["data"]]
    assert ids == ["deepseek/deepseek-chat", "anthropic/claude-haiku-4-5"]
