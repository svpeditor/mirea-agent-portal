"""End-to-end: build echo + run_job → status=ready, артефакты сохранены."""  # noqa: RUF002
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


if shutil.which("docker") is None:
    pytest.skip("docker not available", allow_module_level=True)


@pytest.fixture()
def echo_image_built(tmp_path: Path):
    """Запустить build_agent_version для echo и вернуть docker_image_tag."""  # noqa: RUF002
    repo_root = Path(__file__).resolve().parents[3]
    src = repo_root / "agents" / "echo"
    work = tmp_path / "echo-work"
    bare = tmp_path / "echo.git"
    subprocess.run(["git", "init", "-b", "main", str(work)],
                   check=True, capture_output=True)
    subprocess.run(["cp", "-R", str(src) + "/.", str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "add", "."],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work),
                    "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-m", "init"],
                   check=True, capture_output=True)
    subprocess.run(["git", "clone", "--bare", str(work), str(bare)],
                   check=True, capture_output=True)
    sha = subprocess.run(["git", "-C", str(bare), "rev-parse", "HEAD"],
                         check=True, capture_output=True).stdout.decode().strip()
    return bare, sha


def _setup_job(pg_container, file_store_root: Path, agent_slug: str,
               sha: str, image_tag: str, params: dict, inputs: dict[str, bytes]):
    """Insert necessary rows + материализовать input файлы."""  # noqa: RUF002
    eng = create_engine(pg_container.get_connection_url())
    manifest = {
        "id": "echo", "name": "Echo", "version": "0.1.0",
        "category": "научная-работа", "short_description": "echo",
        "inputs": {
            "message": {"type": "text", "label": "msg", "required": True},
        },
        "files": {},
        "outputs": [
            {"id": "report",  "type": "docx", "label": "doc",
             "filename": "echo.docx", "primary": True},
            {"id": "summary", "type": "json", "label": "json",
             "filename": "summary.json"},
        ],
        "runtime": {
            "docker": {
                "base_image": "python:3.12-slim",
                "setup": ["pip install -r requirements.txt"],
                "entrypoint": ["python", "agent.py"],
            },
            "llm": {"provider": "openrouter", "models": []},
            "limits": {"max_runtime_minutes": 2, "max_memory_mb": 256, "max_cpu_cores": 1},
        },
    }
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES ('e2e@example.com', 'h', 'd') RETURNING id"
        )).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('e2e-tab', 'T') RETURNING id"
        )).scalar_one()
        aid = c.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES (:s, 'Echo', 'd', :tid, :url, :uid) RETURNING id"
        ), {"s": agent_slug, "tid": tid,
            "url": "file:///dev/null", "uid": uid}).scalar_one()
        vid = c.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, docker_image_tag, "
            "created_by_user_id) "
            "VALUES (:aid, :sha, 'main', CAST(:m AS jsonb), '1.0', 'ready', :tag, :uid) "
            "RETURNING id"
        ), {"aid": aid, "sha": sha, "m": json.dumps(manifest),
            "tag": image_tag, "uid": uid}).scalar_one()
        jid = c.execute(text(
            "INSERT INTO jobs (agent_version_id, created_by_user_id, status, params_jsonb) "
            "VALUES (:vid, :uid, 'queued', CAST(:p AS jsonb)) RETURNING id"
        ), {"vid": vid, "uid": uid, "p": json.dumps(params)}).scalar_one()
        for fname, data in inputs.items():
            c.execute(text(
                "INSERT INTO job_files (job_id, kind, filename, size_bytes, "
                "sha256, storage_key) VALUES (:vid, 'input', :n, :s, 'x', :k)"
            ), {"vid": jid, "n": fname, "s": len(data),
                "k": f"{jid}/input/{fname}"})
    eng.dispose()
    input_dir = file_store_root / str(jid) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for fname, data in inputs.items():
        (input_dir / fname).write_bytes(data)
    return jid


@pytest.mark.timeout(900)
def test_full_run_of_echo(
    settings_env, db_with_schema, pg_container, echo_image_built, tmp_path,
    monkeypatch,
) -> None:
    """E2E: build echo → setup job → run_job → status=ready, output файл сохранён."""  # noqa: RUF002
    bare, sha = echo_image_built
    from portal_worker.tasks.build_agent import build_agent_version
    eng = create_engine(pg_container.get_connection_url())
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES ('e2e-build@example.com', 'h', 'd') RETURNING id"
        )).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('e2e-build-tab', 'T') RETURNING id"
        )).scalar_one()
        aid = c.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES ('echo', 'Echo', 'd', :tid, :url, :uid) RETURNING id"
        ), {"tid": tid, "url": f"file://{bare}", "uid": uid}).scalar_one()
        avid = c.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, created_by_user_id) "
            "VALUES (:aid, :sha, 'main', '{}'::jsonb, '0.1.0', 'pending_build', :uid) "
            "RETURNING id"
        ), {"aid": aid, "sha": sha, "uid": uid}).scalar_one()
    eng.dispose()

    monkeypatch.setenv("PORTAL_SDK_PATH",
                       str(Path(__file__).resolve().parents[3]
                           / "packages" / "portal-sdk-python"))
    from portal_worker import config as cfg
    cfg.get_settings.cache_clear()
    build_agent_version(str(avid))

    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        image_tag = c.execute(text(
            "SELECT docker_image_tag FROM agent_versions WHERE id=:v"
        ), {"v": avid}).scalar_one()
    eng.dispose()
    assert image_tag is not None

    file_store_root = tmp_path / "files"
    file_store_root.mkdir()
    monkeypatch.setenv("FILE_STORE_LOCAL_ROOT", str(file_store_root))
    cfg.get_settings.cache_clear()
    jid = _setup_job(pg_container, file_store_root,
                     agent_slug="echo-job", sha=sha, image_tag=image_tag,
                     params={"message": "hello", "loops": 2, "shout": False},
                     inputs={})

    from portal_worker.tasks.run_job import run_job
    run_job(str(jid))

    eng = create_engine(pg_container.get_connection_url())
    with eng.connect() as c:
        status, ec = c.execute(text(
            "SELECT status, error_code FROM jobs WHERE id=:v"
        ), {"v": jid}).one()
        events = c.execute(text(
            "SELECT event_type FROM job_events WHERE job_id=:v ORDER BY seq"
        ), {"v": jid}).all()
        out_files = c.execute(text(
            "SELECT filename, size_bytes FROM job_files WHERE job_id=:v AND kind='output'"
        ), {"v": jid}).all()
    eng.dispose()
    assert status == "ready", f"failed: {ec}"
    assert "started" in [e[0] for e in events]
    assert "result" in [e[0] for e in events]
    out_names = [f[0] for f in out_files]
    assert "echo.docx" in out_names
    assert "summary.json" in out_names

    subprocess.run(["docker", "rmi", "-f", image_tag],
                   check=False, capture_output=True)
