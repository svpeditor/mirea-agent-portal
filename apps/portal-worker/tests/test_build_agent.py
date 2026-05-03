"""End-to-end: build_agent_version assembles echo agent and bad agent."""
import contextlib
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

if shutil.which("docker") is None:
    pytest.skip("docker not available", allow_module_level=True)


@pytest.fixture()
def echo_repo(tmp_path: Path):
    src = Path(__file__).resolve().parents[3] / "agents" / "echo"
    work = tmp_path / "work"
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    subprocess.run(["cp", "-R", str(src) + "/.", str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(work), "-c", "user.name=t", "-c", "user.email=t@t",
         "commit", "-m", "init"], check=True, capture_output=True,
    )
    subprocess.run(["git", "clone", "--bare", str(work), str(bare)],
                   check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "-C", str(bare), "rev-parse", "HEAD"],
        check=True, capture_output=True,
    ).stdout.decode().strip()
    return bare, sha


@pytest.fixture()
def sdk_path():
    return Path(__file__).resolve().parents[3] / "packages" / "portal-sdk-python"


@pytest.fixture()
def setup_version(pg_container, db_with_schema, echo_repo):
    bare, sha = echo_repo
    eng = create_engine(pg_container.get_connection_url())
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name, role)"
            " VALUES ('e@x.com', 'x', 'Echo User', 'admin') RETURNING id"
        )).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('tab-echo', 'N') RETURNING id"
        )).scalar_one()
        aid = c.execute(text("""
            INSERT INTO agents (slug, name, short_description, tab_id, git_url, created_by_user_id)
            VALUES ('echo', 'Echo', 'd', :tid, :url, :uid) RETURNING id
        """), {"tid": tid, "url": f"file://{bare}", "uid": uid}).scalar_one()
        vid = c.execute(text("""
            INSERT INTO agent_versions (agent_id, git_sha, git_ref,
                manifest_jsonb, manifest_version, status, created_by_user_id)
            VALUES (:aid, :sha, 'main', '{"id":"echo"}'::jsonb, '0.1.0',
                    'pending_build', :uid)
            RETURNING id
        """), {"aid": aid, "sha": sha, "uid": uid}).scalar_one()
    eng.dispose()
    return vid, sha


@pytest.mark.asyncio
async def test_full_build_of_echo(
    settings_env, setup_version, pg_container, sdk_path, monkeypatch,
) -> None:
    vid, _sha = setup_version
    monkeypatch.setenv("PORTAL_SDK_PATH", str(sdk_path))
    from portal_worker import config
    config.get_settings.cache_clear()

    from portal_worker.tasks.build_agent import build_agent_version
    build_agent_version(str(vid))

    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        row = c.execute(text("""
            SELECT status, docker_image_tag, build_error
            FROM agent_versions WHERE id = :vid
        """), {"vid": vid}).one()
    eng.dispose()

    assert row.status == "ready", f"build failed: {row.build_error}"
    assert row.docker_image_tag is not None
    assert row.docker_image_tag.startswith("portal/agent-echo:v")

    # Cleanup built image
    import docker as _docker
    with contextlib.suppress(Exception):
        _docker.from_env().images.remove(row.docker_image_tag, force=True)


@pytest.mark.asyncio
async def test_build_with_bad_setup_writes_failed(
    settings_env, db_with_schema, pg_container, sdk_path, tmp_path, monkeypatch,
) -> None:
    """Agent with broken setup -> status=failed, build_error=docker_error."""
    monkeypatch.setenv("PORTAL_SDK_PATH", str(sdk_path))
    from portal_worker import config
    config.get_settings.cache_clear()

    # Bad agent
    bad_src = tmp_path / "bad-src"
    bad_src.mkdir()
    (bad_src / "manifest.yaml").write_text("""
id: bad
name: "Bad"
version: "0.1.0"
category: "scientific-work"
short_description: "bad"
inputs: {}
files: {}
outputs:
  - id: out
    type: any
    label: out
    filename: out.txt
runtime:
  docker:
    base_image: "python:3.12-slim"
    setup: ["pip install non-existent-pkg-xyz-portal-test"]
    entrypoint: ["python", "agent.py"]
  llm:
    provider: openrouter
    models: []
  limits:
    max_runtime_minutes: 1
    max_memory_mb: 128
    max_cpu_cores: 1
""", encoding="utf-8")
    (bad_src / "agent.py").write_text("print('x')\n")

    work = tmp_path / "bad-work"
    bare = tmp_path / "bad.git"
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    subprocess.run(["cp", "-R", str(bad_src) + "/.", str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(work), "-c", "user.name=t", "-c", "user.email=t@t",
         "commit", "-m", "init"], check=True, capture_output=True,
    )
    subprocess.run(["git", "clone", "--bare", str(work), str(bare)],
                   check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "-C", str(bare), "rev-parse", "HEAD"],
        check=True, capture_output=True,
    ).stdout.decode().strip()

    eng = create_engine(pg_container.get_connection_url())
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name, role)"
            " VALUES ('bad@x.com', 'x', 'Bad User', 'admin') RETURNING id"
        )).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('tab-bad', 'N') RETURNING id"
        )).scalar_one()
        aid = c.execute(text("""
            INSERT INTO agents (slug, name, short_description, tab_id, git_url, created_by_user_id)
            VALUES ('bad', 'Bad', 'd', :tid, :url, :uid) RETURNING id
        """), {"tid": tid, "url": f"file://{bare}", "uid": uid}).scalar_one()
        vid = c.execute(text("""
            INSERT INTO agent_versions (agent_id, git_sha, git_ref,
                manifest_jsonb, manifest_version, status, created_by_user_id)
            VALUES (:aid, :sha, 'main', '{"id":"bad"}'::jsonb, '0.1.0',
                    'pending_build', :uid)
            RETURNING id
        """), {"aid": aid, "sha": sha, "uid": uid}).scalar_one()
    eng.dispose()

    from portal_worker.tasks.build_agent import build_agent_version
    build_agent_version(str(vid))

    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        row = c.execute(text("""
            SELECT status, build_error, build_log
            FROM agent_versions WHERE id = :vid
        """), {"vid": vid}).one()
    eng.dispose()

    assert row.status == "failed"
    assert row.build_error == "docker_error"
    assert "non-existent-pkg-xyz" in (row.build_log or "")
