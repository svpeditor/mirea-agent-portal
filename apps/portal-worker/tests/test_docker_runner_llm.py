"""docker_runner: два режима сети, env vars пробрасываются."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from portal_worker.runner.docker_runner import run_agent_container
from portal_worker.runner.llm_runtime_config import LlmRuntimeConfig


@pytest.fixture
def common_args(tmp_path: Path) -> dict:
    inp = tmp_path / "in"
    out = tmp_path / "out"
    inp.mkdir()
    out.mkdir()
    params = tmp_path / "params.json"
    params.write_text("{}")
    return dict(
        image_tag="portal/agent-test:v1",
        input_dir=inp,
        output_dir=out,
        params_path=params,
        memory_mb=256,
        cpu_cores=1.0,
        timeout_seconds=10,
        cancel_check=lambda: False,
        on_event=lambda e: None,
        labels={"job_id": "x"},
    )


def test_no_llm_uses_network_none(common_args) -> None:
    container = MagicMock()
    container.logs.return_value = iter([])
    container.wait.return_value = {"StatusCode": 0}
    client = MagicMock()
    client.containers.run.return_value = container

    with patch("portal_worker.runner.docker_runner.docker.from_env", return_value=client):
        run_agent_container(**common_args, llm_config=None)

    call_kwargs = client.containers.run.call_args.kwargs
    assert call_kwargs.get("network_mode") == "none"
    assert "network" not in call_kwargs
    env = call_kwargs.get("environment", {})
    assert "OPENROUTER_API_KEY" not in env
    assert "OPENROUTER_BASE_URL" not in env


def test_with_llm_joins_agents_network_and_sets_env(common_args) -> None:
    container = MagicMock()
    container.logs.return_value = iter([])
    container.wait.return_value = {"StatusCode": 0}
    client = MagicMock()
    client.containers.run.return_value = container

    cfg = LlmRuntimeConfig(
        ephemeral_token="por-job-deadbeefdeadbeefdeadbeefdeadbeef",
        agents_network_name="portal-agents-net",
        proxy_base_url="http://api:8000/llm/v1",
    )

    with patch("portal_worker.runner.docker_runner.docker.from_env", return_value=client):
        run_agent_container(**common_args, llm_config=cfg)

    call_kwargs = client.containers.run.call_args.kwargs
    assert call_kwargs.get("network") == "portal-agents-net"
    assert call_kwargs.get("network_mode") != "none"
    env = call_kwargs.get("environment", {})
    assert env["OPENROUTER_API_KEY"] == cfg.ephemeral_token
    assert env["OPENROUTER_BASE_URL"] == cfg.proxy_base_url
    assert env["PARAMS_FILE"] == "/var/agent/params.json"
