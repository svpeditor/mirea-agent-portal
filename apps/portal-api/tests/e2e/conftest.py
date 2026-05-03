"""E2E conftest: фикстура `published_echo_llm`."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
async def published_echo_llm(client, admin_token, tmp_path):  # type: ignore[no-untyped-def]
    """Публикует echo-llm fixture как agent_version в статусе ready.

    1. Создаёт временный git-репо из fixtures/echo-llm/
    2. POST /api/admin/agents (git_url=file://...) — атомарно создаёт Agent + AgentVersion
    3. Ждёт build до статуса ready (до 5 мин)
    4. Возвращает (agent_id, agent_version_id)
    """
    fixture_src = Path(__file__).parent / "fixtures" / "echo-llm"
    git_repo = tmp_path / "echo-llm-repo"
    git_repo.mkdir()
    shutil.copytree(fixture_src, git_repo, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=git_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.t", "-c", "user.name=t", "commit", "-q", "-m", "init"],
        cwd=git_repo,
        check=True,
    )
    subprocess.run(["git", "tag", "v0.1.0"], cwd=git_repo, check=True)

    auth = {"Cookie": f"access_token={admin_token}"}

    # POST /api/admin/agents — читает manifest.yaml из репо для slug/name/tab
    r = await client.post(
        "/api/admin/agents",
        headers=auth,
        json={
            "git_url": f"file://{git_repo}",
            "git_ref": "v0.1.0",
        },
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    agent_id = body["agent"]["id"]
    av_id = body["version"]["id"]

    # Ждём build до статуса ready (build выполняется воркером; в unit-тестах не запускается)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        r2 = await client.get(f"/api/admin/agent_versions/{av_id}", headers=auth)
        st = r2.json().get("status")
        if st == "ready":
            return agent_id, av_id
        if st == "failed":
            pytest.fail(f"build failed: {r2.json().get('build_error')}")
        await asyncio.sleep(3)

    pytest.fail("build did not finish in 5 minutes")
