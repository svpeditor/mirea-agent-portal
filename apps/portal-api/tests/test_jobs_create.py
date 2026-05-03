"""POST /api/agents/{slug}/jobs."""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from portal_api.models import Job, JobFile
from tests.factories import make_agent, make_agent_version, make_tab


async def _ready_agent(db, admin_user, slug="echo"):
    tab = await make_tab(db, slug=f"jct-{slug}", name="T", order_idx=1)
    agent = await make_agent(db, slug=slug, tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id,
                                        status="ready")
    agent.current_version_id = version.id
    await db.commit()
    return agent


def _mock_enqueuer():
    """Return a MagicMock that stands in for JobEnqueuer."""
    m = MagicMock()
    m.enqueue_run = MagicMock()
    return m


def _make_settings_override(tmp_path: Path, max_job_input_bytes: int | None = None):
    """Create a get_settings override pointing file store at tmp_path."""
    from portal_api.config import get_settings

    base = get_settings()
    overrides: dict = {"file_store_local_root": tmp_path}
    if max_job_input_bytes is not None:
        overrides["max_job_input_bytes"] = max_job_input_bytes

    # Build a new Settings-like object by copying the base and overriding fields
    import copy
    s = copy.copy(base)
    for k, v in overrides.items():
        object.__setattr__(s, k, v)

    return lambda: s


@pytest.mark.asyncio
async def test_create_job_happy_path(user_client, db, admin_user, tmp_path) -> None:
    from portal_api.deps import get_job_enqueuer, get_settings
    from portal_api.main import app

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer
    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)

    try:
        await _ready_agent(db, admin_user, slug="happy")
        files = {"inputs[a.txt]": ("a.txt", io.BytesIO(b"hello"), "text/plain")}
        data = {"params": json.dumps({"k": "v"})}
        resp = await user_client.post("/api/agents/happy/jobs", files=files, data=data)
        assert resp.status_code == 202
        body = resp.json()
        assert body["job"]["status"] == "queued"
        assert body["job"]["agent_slug"] == "happy"

        job_id = body["job"]["id"]
        job = (await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))).scalar_one()
        assert job.params_jsonb == {"k": "v"}
        files_rows = (await db.execute(
            select(JobFile).where(JobFile.job_id == job.id)
        )).scalars().all()
        assert len(files_rows) == 1
        assert files_rows[0].filename == "a.txt"
        assert files_rows[0].size_bytes == 5

        mock_enqueuer.enqueue_run.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_create_job_unknown_agent_404(user_client) -> None:
    resp = await user_client.post(
        "/api/agents/nope/jobs",
        data={"params": "{}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AGENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_job_disabled_agent_404(user_client, db, admin_user) -> None:
    tab = await make_tab(db, slug="dis-t-c", name="T", order_idx=1)
    agent = await make_agent(db, slug="dis-c", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=False)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = version.id
    await db.commit()
    resp = await user_client.post("/api/agents/dis-c/jobs", data={"params": "{}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_job_version_not_ready_409(user_client, db, admin_user) -> None:
    tab = await make_tab(db, slug="nr-t-c", name="T", order_idx=1)
    agent = await make_agent(db, slug="nr-c", tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    version = await make_agent_version(db, agent_id=agent.id,
                                        created_by_user_id=admin_user.id, status="building")
    agent.current_version_id = version.id
    await db.commit()
    resp = await user_client.post("/api/agents/nr-c/jobs", data={"params": "{}"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "agent_not_ready"


@pytest.mark.asyncio
async def test_create_job_invalid_params_400(user_client, db, admin_user) -> None:
    await _ready_agent(db, admin_user, slug="bad-params")
    resp = await user_client.post(
        "/api/agents/bad-params/jobs", data={"params": "not-json"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "params_invalid_json"


@pytest.mark.asyncio
async def test_create_job_filename_traversal_400(user_client, db, admin_user, tmp_path) -> None:
    from portal_api.deps import get_job_enqueuer, get_settings
    from portal_api.main import app

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer
    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)

    try:
        await _ready_agent(db, admin_user, slug="trav")
        files = {"inputs[../etc/passwd]": ("x", io.BytesIO(b"x"), "text/plain")}
        resp = await user_client.post(
            "/api/agents/trav/jobs", files=files, data={"params": "{}"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "input_filename_invalid"
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_create_job_inputs_too_large_413(user_client, db, admin_user, tmp_path) -> None:
    from portal_api.deps import get_job_enqueuer, get_settings
    from portal_api.main import app
    from portal_api.models import Agent

    mock_enqueuer = _mock_enqueuer()
    app.dependency_overrides[get_job_enqueuer] = lambda: mock_enqueuer
    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path, max_job_input_bytes=10)

    try:
        await _ready_agent(db, admin_user, slug="big")
        files = {"inputs[a.txt]": ("a.txt", io.BytesIO(b"x" * 100), "text/plain")}
        resp = await user_client.post(
            "/api/agents/big/jobs", files=files, data={"params": "{}"},
        )
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "inputs_too_large"

        # Verify DB rollback — no Job row for this agent
        agent = (await db.execute(select(Agent).where(Agent.slug == "big"))).scalar_one()
        jobs_for_agent = (await db.execute(
            select(Job).where(Job.agent_version_id == agent.current_version_id)
        )).scalars().all()
        assert jobs_for_agent == [], "rejected upload should leave no Job row"

        # Verify disk cleanup — no leftover files under tmp_path
        leftover_files = list(tmp_path.rglob("*"))
        leftover_files = [f for f in leftover_files if f.is_file()]
        assert leftover_files == [], f"disk leak: found {leftover_files}"
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)
        app.dependency_overrides.pop(get_settings, None)
