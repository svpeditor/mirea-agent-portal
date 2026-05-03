"""POST /api/agents/{slug}/jobs для агента с runtime.llm создаёт ephemeral_token."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa

from portal_api.models import EphemeralToken, UserQuota
from tests.factories import (
    make_agent, make_agent_version, make_tab,
)


def _mock_enqueuer():
    m = MagicMock()
    m.enqueue_run = MagicMock()
    return m


@pytest.mark.asyncio
async def test_create_job_with_llm_inserts_ephemeral_token(
    db, client, normal_user, normal_user_token, admin_user,
) -> None:
    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer

    try:
        tab = await make_tab(db, slug="t-cl", name="T", order_idx=1)
        agent = await make_agent(db, slug="proverka", tab_id=tab.id,
                                 created_by_user_id=admin_user.id, enabled=True)
        av = await make_agent_version(
            db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
            manifest_jsonb={
                "runtime": {
                    "llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]},
                    "limits": {"max_runtime_minutes": 60},
                }
            },
        )
        agent.current_version_id = av.id
        await db.commit()

        r = await client.post(
            f"/api/agents/{agent.slug}/jobs",
            headers={"Cookie": f"access_token={normal_user_token}"},
            files={"params": (None, '{"x":1}')},
        )
        assert r.status_code in (200, 201, 202), r.text
        job_id = r.json()["job"]["id"]

        tokens = (await db.execute(
            sa.select(EphemeralToken).where(EphemeralToken.job_id == job_id)
        )).scalars().all()
        assert len(tokens) == 1
        assert tokens[0].user_id == normal_user.id
        assert tokens[0].agent_version_id == av.id
        assert tokens[0].revoked_at is None
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)


@pytest.mark.asyncio
async def test_create_job_without_llm_no_token(
    db, client, normal_user, normal_user_token, admin_user,
) -> None:
    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer

    try:
        tab = await make_tab(db, slug="t-cl2", name="T", order_idx=1)
        agent = await make_agent(db, slug="echo", tab_id=tab.id,
                                 created_by_user_id=admin_user.id, enabled=True)
        av = await make_agent_version(
            db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
            manifest_jsonb={"runtime": {"limits": {"max_runtime_minutes": 5}}},
        )
        agent.current_version_id = av.id
        await db.commit()

        r = await client.post(
            f"/api/agents/{agent.slug}/jobs",
            headers={"Cookie": f"access_token={normal_user_token}"},
            files={"params": (None, '{}')},
        )
        assert r.status_code in (200, 201, 202), r.text
        job_id = r.json()["job"]["id"]

        tokens = (await db.execute(
            sa.select(EphemeralToken).where(EphemeralToken.job_id == job_id)
        )).scalars().all()
        assert len(tokens) == 0
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)


@pytest.mark.asyncio
async def test_create_job_quota_exhausted_returns_402(
    db, client, normal_user, normal_user_token, admin_user,
) -> None:
    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer

    try:
        quota = await db.get(UserQuota, normal_user.id)
        quota.period_used_usd = Decimal("5.0001")
        await db.commit()

        tab = await make_tab(db, slug="t-cl3", name="T", order_idx=1)
        agent = await make_agent(db, slug="proverka2", tab_id=tab.id,
                                 created_by_user_id=admin_user.id, enabled=True)
        av = await make_agent_version(
            db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
            manifest_jsonb={"runtime": {"llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]}, "limits": {"max_runtime_minutes": 60}}},
        )
        agent.current_version_id = av.id
        await db.commit()

        r = await client.post(
            f"/api/agents/{agent.slug}/jobs",
            headers={"Cookie": f"access_token={normal_user_token}"},
            files={"params": (None, '{}')},
        )
        assert r.status_code == 402, r.text
        assert r.json()["error"]["code"] == "quota_exhausted"
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)
