"""run_job: при наличии runtime.llm передаёт LlmRuntimeConfig + revoke в finally."""
from __future__ import annotations

import json
from unittest.mock import patch

from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer


def _insert_job_with_llm(pg_container: PostgresContainer) -> object:
    """Вставить user/tab/agent/agent_version/job с runtime.llm в manifest."""
    manifest = {
        "id": "rj-llm", "name": "RJ-LLM", "version": "0.1.0",
        "category": "научная-работа", "short_description": "d",
        "inputs": {}, "files": {},
        "outputs": [{"id": "o", "type": "any", "label": "o", "filename": "out.txt"}],
        "runtime": {
            "docker": {
                "base_image": "python:3.12-slim",
                "setup": [], "entrypoint": ["python", "agent.py"],
            },
            "llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]},
            "limits": {"max_runtime_minutes": 5, "max_memory_mb": 256, "max_cpu_cores": 1},
        },
    }
    eng = create_engine(pg_container.get_connection_url())
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES ('rjllm@x.x', 'h', 'd') RETURNING id"
        )).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('t-rjllm', 'T') RETURNING id"
        )).scalar_one()
        aid = c.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES ('a-rjllm', 'A', 'd', :tid, 'https://x', :uid) RETURNING id"
        ), {"tid": tid, "uid": uid}).scalar_one()
        vid = c.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, docker_image_tag, "
            "created_by_user_id) "
            "VALUES (:aid, :sha, 'main', CAST(:m AS jsonb), '1.0', 'ready', "
            "'portal/agent-test:v1', :uid) RETURNING id"
        ), {"aid": aid, "sha": "aa" * 20, "m": json.dumps(manifest), "uid": uid}).scalar_one()
        jid = c.execute(text(
            "INSERT INTO jobs (agent_version_id, created_by_user_id, status, params_jsonb) "
            "VALUES (:vid, :uid, 'queued', '{}') RETURNING id"
        ), {"vid": vid, "uid": uid}).scalar_one()
    eng.dispose()
    return jid


def _insert_job_without_llm(pg_container: PostgresContainer) -> object:
    """Вставить user/tab/agent/agent_version/job БЕЗ runtime.llm в manifest."""
    manifest = {
        "id": "rj-nollm", "name": "RJ-NOLLM", "version": "0.1.0",
        "category": "научная-работа", "short_description": "d",
        "inputs": {}, "files": {},
        "outputs": [{"id": "o", "type": "any", "label": "o", "filename": "out.txt"}],
        "runtime": {
            "docker": {
                "base_image": "python:3.12-slim",
                "setup": [], "entrypoint": ["python", "agent.py"],
            },
            "limits": {"max_runtime_minutes": 5, "max_memory_mb": 256, "max_cpu_cores": 1},
        },
    }
    eng = create_engine(pg_container.get_connection_url())
    with eng.begin() as c:
        uid = c.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES ('rjnollm@x.x', 'h', 'd') RETURNING id"
        )).scalar_one()
        tid = c.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('t-rjnollm', 'T') RETURNING id"
        )).scalar_one()
        aid = c.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES ('a-rjnollm', 'A', 'd', :tid, 'https://x', :uid) RETURNING id"
        ), {"tid": tid, "uid": uid}).scalar_one()
        vid = c.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, docker_image_tag, "
            "created_by_user_id) "
            "VALUES (:aid, :sha, 'main', CAST(:m AS jsonb), '1.0', 'ready', "
            "'portal/agent-test:v2', :uid) RETURNING id"
        ), {"aid": aid, "sha": "bb" * 20, "m": json.dumps(manifest), "uid": uid}).scalar_one()
        jid = c.execute(text(
            "INSERT INTO jobs (agent_version_id, created_by_user_id, status, params_jsonb) "
            "VALUES (:vid, :uid, 'queued', '{}') RETURNING id"
        ), {"vid": vid, "uid": uid}).scalar_one()
    eng.dispose()
    return jid


def test_run_job_with_llm_passes_config_and_revokes(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    """Mock'аем docker_runner и проверяем что LlmRuntimeConfig передан + revoke вызван."""
    from portal_worker.tasks import run_job as rj

    jid = _insert_job_with_llm(pg_container)
    captured_kwargs: dict = {}
    revoke_calls: list = []

    def fake_run_agent_container(**kwargs):
        captured_kwargs.update(kwargs)
        return 0

    def fake_revoke(job_id):
        revoke_calls.append(job_id)

    with (
        patch.object(rj, "run_agent_container", fake_run_agent_container),
        patch.object(rj, "revoke_ephemeral_token_in_db", fake_revoke),
    ):
        payload = {
            "job_id": str(jid),
            "ephemeral_token": "por-job-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        }
        rj.run_job(payload)

    assert "llm_config" in captured_kwargs
    cfg = captured_kwargs["llm_config"]
    assert cfg is not None
    assert cfg.ephemeral_token == payload["ephemeral_token"]
    assert len(revoke_calls) == 1
    assert str(revoke_calls[0]) == str(jid)


def test_run_job_without_llm_no_config_no_revoke(
    settings_env: None, db_with_schema: None, pg_container: PostgresContainer,
) -> None:
    """Без runtime.llm — llm_config=None и revoke не вызывается."""
    from portal_worker.tasks import run_job as rj

    jid = _insert_job_without_llm(pg_container)
    captured_kwargs: dict = {}
    revoke_calls: list = []

    def fake_run_agent_container(**kwargs):
        captured_kwargs.update(kwargs)
        return 0

    def fake_revoke(job_id):
        revoke_calls.append(job_id)

    with (
        patch.object(rj, "run_agent_container", fake_run_agent_container),
        patch.object(rj, "revoke_ephemeral_token_in_db", fake_revoke),
    ):
        payload = {"job_id": str(jid)}
        rj.run_job(payload)

    assert captured_kwargs.get("llm_config") is None
    assert revoke_calls == []
