"""Тесты локального запуска агента без портала."""
# ruff: noqa: RUF002, RUF003
import io
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from portal_sdk.local_runner import run


def test_run_echoes_message(fixtures_dir: Path, tmp_path: Path) -> None:
    """Агент получает params, пишет файл, возвращает result."""
    agent_dir = fixtures_dir / "dummy_agent"
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    log_buf = io.StringIO()

    exit_code = run(
        agent_dir=agent_dir,
        params={"message": "привет"},
        files={},
        output_dir=output_dir,
        log=log_buf,
    )

    assert exit_code == 0, f"agent failed:\n{log_buf.getvalue()}"
    assert (output_dir / "echoed.txt").read_text(encoding="utf-8") == "привет"


def test_run_streams_events(fixtures_dir: Path, tmp_path: Path) -> None:
    agent_dir = fixtures_dir / "dummy_agent"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    log_buf = io.StringIO()

    run(agent_dir=agent_dir, params={"message": "x"}, files={}, output_dir=output_dir, log=log_buf)

    log = log_buf.getvalue()
    # В логе должны мелькнуть «started», «progress», «result»
    assert "started" in log
    assert "progress" in log
    assert "result" in log


def test_run_with_files_input(fixtures_dir: Path, tmp_path: Path) -> None:
    """files-параметр копируется в input_dir, runner принимает даже если агент его не использует."""
    agent_dir = fixtures_dir / "dummy_agent"
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    src = tmp_path / "src"
    src.mkdir()
    (src / "hello.txt").write_text("data")

    log_buf = io.StringIO()

    run(
        agent_dir=agent_dir,
        params={"message": "x"},
        files={"some_input": src},
        output_dir=output_dir,
        log=log_buf,
    )

    # просто убедиться что не упал
    assert (output_dir / "echoed.txt").exists()


def test_run_invalid_manifest_raises(tmp_path: Path) -> None:
    """Если manifest.yaml поломан — runner кидает раньше запуска."""
    agent_dir = tmp_path / "bad"
    agent_dir.mkdir()
    (agent_dir / "manifest.yaml").write_text("not: a valid: manifest")
    (agent_dir / "agent.py").write_text("")

    out = tmp_path / "out"
    out.mkdir()

    with pytest.raises((yaml.YAMLError, ValidationError)):
        run(agent_dir=agent_dir, params={}, files={}, output_dir=out, log=io.StringIO())
