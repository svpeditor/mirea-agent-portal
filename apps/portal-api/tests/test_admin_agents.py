"""Тесты POST /api/admin/agents — создание агента + первой версии + enqueue билда."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from redis import Redis
from rq import Queue
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Agent, AgentVersion, Tab, User
from tests.factories import make_agent, make_agent_version, make_tab


async def _clear_tabs(db: AsyncSession) -> None:
    """Удалить все pre-bootstrap вкладки + агентов, чтобы тест работал в изоляции."""
    await db.execute(delete(AgentVersion))
    await db.execute(delete(Agent))
    await db.execute(delete(Tab))
    await db.flush()


@pytest.fixture
def echo_bare_repo(tmp_path: Path) -> Path:
    """Создаёт bare-репо из локальной директории agents/echo/."""
    repo_root = (
        Path(__file__).resolve().parent.parent.parent.parent / "agents" / "echo"
    )
    assert repo_root.is_dir(), f"Repo not found: {repo_root}"

    work = tmp_path / "work"
    work.mkdir()
    shutil.copytree(repo_root, work, dirs_exist_ok=True)
    bare = tmp_path / "echo.git"

    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(work), "add", "-A"], check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-m",
            "init",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)],
        check=True,
        capture_output=True,
    )
    return bare


@pytest_asyncio.fixture
async def admin_client_with_redis(
    admin_client: AsyncClient,
    redis_url: str,
    reset_redis: None,
) -> AsyncClient:
    """admin_client с переопределённым get_build_enqueuer на тестовый redis_url."""
    from portal_api.deps import get_build_enqueuer
    from portal_api.main import app
    from portal_api.services.build_enqueue import BuildEnqueuer

    def _override_enqueuer() -> BuildEnqueuer:
        return BuildEnqueuer(redis_url)

    app.dependency_overrides[get_build_enqueuer] = _override_enqueuer
    return admin_client


@pytest.mark.asyncio
async def test_create_agent_enqueues_build(
    db: AsyncSession,
    admin_client_with_redis: AsyncClient,
    echo_bare_repo: Path,
    redis_url: str,
) -> None:
    await _clear_tabs(db)
    # echo.manifest.category="научная-работа" — создаём такую вкладку
    await make_tab(db, slug="научная-работа", name="Научная", order_idx=10)
    await db.commit()

    resp = await admin_client_with_redis.post(
        "/api/admin/agents",
        json={"git_url": f"file://{echo_bare_repo}", "git_ref": "main"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # Ответ содержит agent + version
    assert body["agent"]["slug"] == "echo"
    assert body["agent"]["name"]
    assert body["agent"]["enabled"] is False
    assert body["agent"]["current_version_id"] is None
    assert body["version"]["status"] == "pending_build"
    version_id = uuid.UUID(body["version"]["id"])

    # БД: agent + version созданы, status pending_build
    res = await db.execute(select(Agent).where(Agent.slug == "echo"))
    agent = res.scalar_one()
    assert agent.enabled is False
    assert agent.current_version_id is None

    res = await db.execute(select(AgentVersion).where(AgentVersion.id == version_id))
    version = res.scalar_one()
    assert version.status == "pending_build"
    assert version.agent_id == agent.id
    assert len(version.git_sha) == 40
    assert version.manifest_version == "0.1.0"

    # Redis: задача в очереди builds с version_id в args
    q = Queue("builds", connection=Redis.from_url(redis_url))
    assert q.count == 1
    job = q.jobs[0]
    assert job.args == (str(version_id),)


@pytest.mark.asyncio
async def test_create_agent_unknown_category_falls_back_to_uncategorized(
    db: AsyncSession,
    admin_client_with_redis: AsyncClient,
    tmp_path: Path,
) -> None:
    await _clear_tabs(db)
    # Только uncategorized в БД — никакой "custom-cat"
    uncat = await make_tab(
        db, slug="uncategorized", name="Без категории", order_idx=999, is_system=True
    )
    await db.commit()

    # Сделать кастомный agent-репо с category="custom-cat"
    repo_root = _make_custom_category_repo(tmp_path, category="custom-cat", agent_id="custom")

    resp = await admin_client_with_redis.post(
        "/api/admin/agents",
        json={"git_url": f"file://{repo_root}", "git_ref": "main"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["agent"]["slug"] == "custom"
    assert body["agent"]["tab_id"] == str(uncat.id)

    res = await db.execute(select(Agent).where(Agent.slug == "custom"))
    agent = res.scalar_one()
    assert agent.tab_id == uncat.id


@pytest.mark.asyncio
async def test_create_agent_duplicate_slug_409(
    db: AsyncSession,
    admin_client_with_redis: AsyncClient,
    echo_bare_repo: Path,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="научная-работа", name="Научная", order_idx=10)
    await make_agent(
        db,
        slug="echo",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    await db.commit()

    resp = await admin_client_with_redis.post(
        "/api/admin/agents",
        json={"git_url": f"file://{echo_bare_repo}", "git_ref": "main"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "AGENT_SLUG_TAKEN"


@pytest.mark.asyncio
async def test_create_agent_invalid_git_url_400(
    db: AsyncSession,
    admin_client_with_redis: AsyncClient,
) -> None:
    resp = await admin_client_with_redis.post(
        "/api/admin/agents",
        json={"git_url": "ftp://invalid/x.git", "git_ref": "main"},
    )
    # AnyUrl пропускает ftp://, но resolve_git_ref отбраковывает по scheme.
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "INVALID_GIT_URL"


@pytest.mark.asyncio
async def test_create_agent_unreachable_url_400(
    db: AsyncSession,
    admin_client_with_redis: AsyncClient,
) -> None:
    resp = await admin_client_with_redis.post(
        "/api/admin/agents",
        json={
            "git_url": "https://nonexistent-x.example.invalid/x.git",
            "git_ref": "main",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "INVALID_GIT_URL"


# --- GET /api/admin/agents (list + single) ---


@pytest.mark.asyncio
async def test_list_agents_includes_disabled(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t1", name="Tab1", order_idx=1)
    await make_agent(
        db,
        slug="enabled-agent",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
        enabled=True,
    )
    await make_agent(
        db,
        slug="disabled-agent",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
        enabled=False,
    )
    await db.commit()

    resp = await admin_client.get("/api/admin/agents")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = {a["slug"] for a in body}
    assert "enabled-agent" in slugs
    assert "disabled-agent" in slugs


@pytest.mark.asyncio
async def test_get_agent_returns_versions_list(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t1", name="Tab1", order_idx=1)
    agent = await make_agent(
        db,
        slug="solo",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
        status="ready",
    )
    await db.commit()

    resp = await admin_client.get(f"/api/admin/agents/{agent.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == "solo"
    assert body["id"] == str(agent.id)
    assert body["latest_version"] is not None
    assert body["latest_version"]["status"] == "ready"


@pytest.mark.asyncio
async def test_get_404_on_unknown(
    db: AsyncSession,
    admin_client: AsyncClient,
) -> None:
    await _clear_tabs(db)
    await db.commit()

    resp = await admin_client.get(f"/api/admin/agents/{uuid.uuid4()}")
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "AGENT_NOT_FOUND"


# --- PATCH /api/admin/agents/{id} ---


@pytest.mark.asyncio
async def test_patch_agent_move_tab(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    src = await make_tab(db, slug="src", name="Src", order_idx=1)
    dst = await make_tab(db, slug="dst", name="Dst", order_idx=2)
    agent = await make_agent(
        db,
        slug="movable",
        tab_id=src.id,
        created_by_user_id=admin_user.id,
    )
    await db.commit()

    resp = await admin_client.patch(
        f"/api/admin/agents/{agent.id}",
        json={"tab_id": str(dst.id)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tab_id"] == str(dst.id)

    res = await db.execute(select(Agent).where(Agent.id == agent.id))
    fresh = res.scalar_one()
    await db.refresh(fresh)
    assert fresh.tab_id == dst.id


@pytest.mark.asyncio
async def test_patch_agent_enable_without_current_version_409(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t1", name="Tab1", order_idx=1)
    agent = await make_agent(
        db,
        slug="no-current",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
        enabled=False,
        current_version_id=None,
    )
    await db.commit()

    resp = await admin_client.patch(
        f"/api/admin/agents/{agent.id}",
        json={"enabled": True},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "NO_READY_VERSION"


# --- DELETE /api/admin/agents/{id} ---


@pytest.mark.asyncio
async def test_delete_agent_with_versions_409(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t1", name="Tab1", order_idx=1)
    agent = await make_agent(
        db,
        slug="hasversions",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    await make_agent_version(
        db,
        agent_id=agent.id,
        created_by_user_id=admin_user.id,
    )
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/agents/{agent.id}")
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "AGENT_HAS_VERSIONS"


@pytest.mark.asyncio
async def test_delete_agent_no_versions_204(
    db: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
) -> None:
    await _clear_tabs(db)
    tab = await make_tab(db, slug="t1", name="Tab1", order_idx=1)
    agent = await make_agent(
        db,
        slug="empty",
        tab_id=tab.id,
        created_by_user_id=admin_user.id,
    )
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/agents/{agent.id}")
    assert resp.status_code == 204, resp.text

    res = await db.execute(select(Agent).where(Agent.id == agent.id))
    assert res.scalar_one_or_none() is None


# --- helpers ---


def _make_custom_category_repo(tmp_path: Path, *, category: str, agent_id: str) -> Path:
    """Создаёт bare-репо из echo с переписанным manifest.category и id."""
    src = Path(__file__).resolve().parent.parent.parent.parent / "agents" / "echo"
    work = tmp_path / "custom-work"
    work.mkdir()
    shutil.copytree(src, work, dirs_exist_ok=True)

    # Переписать manifest.yaml через safe_load + safe_dump
    import yaml

    manifest_path = work / "manifest.yaml"
    data: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    data["id"] = agent_id
    data["category"] = category
    manifest_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    bare = tmp_path / f"{agent_id}.git"
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(work), "add", "-A"], check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-m",
            "init",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)],
        check=True,
        capture_output=True,
    )
    return bare
