"""docker_runner.run_agent_container — реальный docker run + stream."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

if shutil.which("docker") is None:
    pytest.skip("docker not available", allow_module_level=True)


def _build_test_image(
    tag: str,
    dockerfile_text: str,
    tmp_path: Path,
    extra_files: dict[str, str] | None = None,
) -> None:
    ctx = tmp_path / "ctx"
    ctx.mkdir(exist_ok=True)
    (ctx / "Dockerfile").write_text(dockerfile_text)
    for name, content in (extra_files or {}).items():
        (ctx / name).write_text(content)
    subprocess.run(
        ["docker", "build", "-t", tag, str(ctx)], check=True, capture_output=True,
    )


@pytest.fixture()
def echo_event_image(tmp_path: Path) -> Any:
    tag = "portal-test/runner-events:t1"
    agent_py = (
        "#!/usr/bin/env python\n"
        "import json\nimport sys\n"
        'for e in [{"type":"started"},{"type":"progress","value":0.5},'
        '{"type":"result","artifacts":[]}]:\n'
        "    print(json.dumps(e))\n"
        "    sys.stdout.flush()\n"
    )
    _build_test_image(tag, """
FROM python:3.12-slim
WORKDIR /agent
COPY agent.py /agent/agent.py
RUN useradd -m agent && chown -R agent /agent
USER agent
ENTRYPOINT ["python", "/agent/agent.py"]
""", tmp_path, extra_files={"agent.py": agent_py})
    yield tag
    subprocess.run(["docker", "rmi", "-f", tag], check=False, capture_output=True)


def test_run_streams_events(echo_event_image: str, tmp_path: Path) -> None:
    from portal_worker.runner.docker_runner import run_agent_container

    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    params_path = tmp_path / "params.json"
    params_path.write_text("{}")

    events: list[dict[str, Any]] = []
    exit_code = run_agent_container(
        image_tag=echo_event_image,
        input_dir=input_dir, output_dir=output_dir, params_path=params_path,
        memory_mb=128, cpu_cores=1.0, timeout_seconds=60,
        cancel_check=lambda: False,
        on_event=events.append,
        labels={"portal-test": "1"},
    )
    assert exit_code == 0
    types = [e["type"] for e in events]
    assert types == ["started", "progress", "result"]


def test_run_timeout_triggers_sigterm(tmp_path: Path) -> None:
    from portal_worker.runner.docker_runner import RunTimeout, run_agent_container

    tag = "portal-test/runner-timeout:t1"
    _build_test_image(tag, """
FROM python:3.12-slim
WORKDIR /agent
RUN echo 'import time\\nwhile True: time.sleep(1)' > /agent/agent.py
ENTRYPOINT ["python", "/agent/agent.py"]
""", tmp_path)
    try:
        input_dir = tmp_path / "ti"
        input_dir.mkdir()
        output_dir = tmp_path / "to"
        output_dir.mkdir()
        params_path = tmp_path / "tp.json"
        params_path.write_text("{}")

        with pytest.raises(RunTimeout):
            run_agent_container(
                image_tag=tag,
                input_dir=input_dir, output_dir=output_dir, params_path=params_path,
                memory_mb=128, cpu_cores=1.0, timeout_seconds=3,
                cancel_check=lambda: False,
                on_event=lambda _e: None,
                labels={"portal-test": "1"},
            )
    finally:
        subprocess.run(["docker", "rmi", "-f", tag], check=False, capture_output=True)


def test_run_cancel_callback_stops_container(tmp_path: Path) -> None:
    from portal_worker.runner.docker_runner import RunCancelled, run_agent_container

    tag = "portal-test/runner-cancel:t1"
    _build_test_image(tag, """
FROM python:3.12-slim
WORKDIR /agent
RUN echo 'import time\\nwhile True: time.sleep(1)' > /agent/agent.py
ENTRYPOINT ["python", "/agent/agent.py"]
""", tmp_path)
    try:
        calls = {"n": 0}

        def cancel_check() -> bool:
            calls["n"] += 1
            return calls["n"] > 2  # отмена через ~2 проверки

        input_dir = tmp_path / "ci"
        input_dir.mkdir()
        output_dir = tmp_path / "co"
        output_dir.mkdir()
        params_path = tmp_path / "cp.json"
        params_path.write_text("{}")

        with pytest.raises(RunCancelled):
            run_agent_container(
                image_tag=tag,
                input_dir=input_dir, output_dir=output_dir, params_path=params_path,
                memory_mb=128, cpu_cores=1.0, timeout_seconds=60,
                cancel_check=cancel_check,
                on_event=lambda _e: None,
                labels={"portal-test": "1"},
            )
    finally:
        subprocess.run(["docker", "rmi", "-f", tag], check=False, capture_output=True)
