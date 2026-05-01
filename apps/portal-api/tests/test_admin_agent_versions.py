"""Admin agent_versions — list / get / new / set_current / retry / delete."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Agent, AgentVersion, Tab, User
from tests.factories import make_agent, make_agent_version, make_tab


def _manifest_stub(agent_id: str = "agent-test", name: str = "T") -> dict[str, Any]:
    """Сжатый manifest_jsonb для фикстур."""
    return {
        "id": agent_id,
        "name": name,
        "version": "0.1.0",
        "category": "научная-работа",
        "icon": "🧪",
        "short_description": "тестовая версия",
        "inputs": {},
        "files": {},
        "outputs": [
            {
                "id": "report",
                "type": "docx",
                "label": "r",
                "filename": "r.docx",
                "primary": True,
            }
        ],
        "runtime": {
            "docker": {
                "base_image": "python:3.12-slim",
                "setup": [],
                "entrypoint": ["python", "agent.py"],
            },
            "llm": {"provider": "openrouter", "models": []},
            "limits": {
                "max_runtime_minutes": 2,
                "max_memory_mb": 128,
                "max_cpu_cores": 1,
            },
        },
    }


async def _clear(db: AsyncSession) -> None:
    await db.execute(delete(AgentVersion))
    await db.execute(delete(Agent))
    await db.execute(delete(Tab))
    await db.flush()


@pytest_asyncio.fixture
async def setup_agent(
    db: AsyncSession, admin_user: User
) -> tuple[Tab, Agent, AgentVersion]:
    """Возвращает (tab, agent, version_ready)."""
    await _clear(db)
    tab = await make_tab(db, slug="t-v", name="V", order_idx=0)
    agent = await make_agent(
        db,
        slug="vt",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    v = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        git_sha="a" * 40,
        status="ready",
        manifest_jsonb=_manifest_stub(),
        manifest_version="0.1.0",
    )
    await db.commit()
    return tab, agent, v


@pytest.mark.asyncio
async def test_list_versions(
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
) -> None:
    _, agent, v = setup_agent
    resp = await admin_client.get(f"/api/admin/agents/{agent.id}/versions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == str(v.id)
    assert body[0]["status"] == "ready"
    assert body[0]["is_current"] is False


@pytest.mark.asyncio
async def test_get_version_detail_returns_manifest(
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
) -> None:
    _, _, v = setup_agent
    resp = await admin_client.get(f"/api/admin/agent_versions/{v.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["manifest_jsonb"]["id"] == "agent-test"


@pytest.mark.asyncio
async def test_get_404_on_unknown_version(admin_client: AsyncClient) -> None:
    resp = await admin_client.get(f"/api/admin/agent_versions/{uuid.uuid4()}")
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "VERSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_new_version_duplicate_sha_409(
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Дважды добавить версию с тем же SHA → 409."""
    _, agent, v = setup_agent

    from portal_api.services import agent_version_service as svc
    from portal_api.services.build_enqueue import BuildEnqueuer

    monkeypatch.setattr(BuildEnqueuer, "enqueue_build", lambda self, vid: None)

    async def fake_resolve(_url: str, _ref: str) -> str:
        return v.git_sha

    async def fake_clone(_url: str, _sha: str) -> dict[str, Any]:
        return _manifest_stub()

    monkeypatch.setattr(svc, "resolve_git_ref", fake_resolve)
    monkeypatch.setattr(svc, "_shallow_clone_for_manifest", fake_clone)

    resp = await admin_client.post(
        f"/api/admin/agents/{agent.id}/versions",
        json={"git_ref": "main"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "VERSION_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_set_current_makes_version_current(
    db: AsyncSession,
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
) -> None:
    _, agent, v = setup_agent
    resp = await admin_client.post(
        f"/api/admin/agent_versions/{v.id}/set_current"
    )
    assert resp.status_code == 200, resp.text

    await db.refresh(agent)
    assert agent.current_version_id == v.id
    # name/icon/short_description обновлены из manifest_jsonb
    assert agent.name == v.manifest_jsonb["name"]
    assert agent.icon == v.manifest_jsonb["icon"]
    assert agent.short_description == v.manifest_jsonb["short_description"]


@pytest.mark.asyncio
async def test_set_current_failed_409(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear(db)
    tab = await make_tab(db, slug="t-fail", name="F", order_idx=0)
    agent = await make_agent(
        db,
        slug="failed-agent",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    v = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        status="failed",
        git_sha="c" * 40,
        manifest_jsonb=_manifest_stub(agent_id="failed", name="F"),
        manifest_version="0.1.0",
    )
    await db.commit()

    resp = await admin_client.post(
        f"/api/admin/agent_versions/{v.id}/set_current"
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "VERSION_NOT_READY"


@pytest.mark.asyncio
async def test_retry_failed_resets_status_and_enqueues(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _clear(db)
    tab = await make_tab(db, slug="t-rt", name="R", order_idx=0)
    agent = await make_agent(
        db,
        slug="retry-agent",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    v = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        status="failed",
        git_sha="d" * 40,
        manifest_jsonb=_manifest_stub(agent_id="retry", name="R"),
        manifest_version="0.1.0",
    )
    v.build_log = "old log"
    v.build_error = "docker_error"
    await db.commit()

    enqueued: list[str] = []
    from portal_api.services.build_enqueue import BuildEnqueuer

    monkeypatch.setattr(
        BuildEnqueuer,
        "enqueue_build",
        lambda self, vid: enqueued.append(str(vid)),
    )

    resp = await admin_client.post(f"/api/admin/agent_versions/{v.id}/retry")
    assert resp.status_code == 200, resp.text
    assert enqueued == [str(v.id)]
    await db.refresh(v)
    assert v.status == "pending_build"
    assert v.build_log is None
    assert v.build_error is None
    assert v.build_started_at is None
    assert v.build_finished_at is None


@pytest.mark.asyncio
async def test_retry_ready_400(
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
) -> None:
    _, _, v = setup_agent  # status='ready'
    resp = await admin_client.post(f"/api/admin/agent_versions/{v.id}/retry")
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "RETRY_NOT_FAILED"


@pytest.mark.asyncio
async def test_delete_current_409(
    db: AsyncSession,
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
) -> None:
    _, agent, v = setup_agent
    agent.current_version_id = v.id
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/agent_versions/{v.id}")
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "VERSION_IS_CURRENT"


@pytest.mark.asyncio
async def test_delete_non_current_204(
    db: AsyncSession,
    admin_client: AsyncClient,
    setup_agent: tuple[Tab, Agent, AgentVersion],
    admin_user: User,
) -> None:
    _, agent, _ = setup_agent
    extra = await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        status="failed",
        git_sha="e" * 40,
        manifest_jsonb=_manifest_stub(agent_id="extra", name="E"),
        manifest_version="0.1.0",
    )
    await db.commit()

    # docker rmi мокаем (best-effort cleanup не должен ломать тест).
    # docker_image_tag=None → cleanup ветка не сработает.
    resp = await admin_client.delete(f"/api/admin/agent_versions/{extra.id}")
    assert resp.status_code == 204, resp.text
