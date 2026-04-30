"""Тесты публичного API класса Agent."""
import io
import json
from pathlib import Path

import pytest

from portal_sdk.agent import Agent


@pytest.fixture
def setup_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Подготовить env-переменные так, как это сделает портал в проде."""
    params_file = tmp_path / "params.json"
    params_file.write_text(
        json.dumps({"section": "robotics", "strict_mode": True}, ensure_ascii=False),
        encoding="utf-8",
    )

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    (input_dir / "works_folder").mkdir()
    (input_dir / "works_folder" / "01").mkdir()
    (input_dir / "works_folder" / "01" / "text.docx").write_text("hello")

    monkeypatch.setenv("PARAMS_FILE", str(params_file))
    monkeypatch.setenv("INPUT_DIR", str(input_dir))
    monkeypatch.setenv("OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://example.test/v1")

    return {"params_file": params_file, "input_dir": input_dir, "output_dir": output_dir}


def test_agent_reads_params(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    assert agent.params == {"section": "robotics", "strict_mode": True}


def test_input_dir_returns_subpath(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    works = agent.input_dir("works_folder")
    assert works == setup_env["input_dir"] / "works_folder"
    assert (works / "01" / "text.docx").exists()


def test_input_dir_unknown_id_raises(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    with pytest.raises(FileNotFoundError):
        agent.input_dir("nonexistent")


def test_output_dir_property(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    assert agent.output_dir == setup_env["output_dir"]


def test_env_proxy(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    assert agent.env["OPENROUTER_API_KEY"] == "test-key"
    assert agent.env["OPENROUTER_BASE_URL"] == "https://example.test/v1"


def test_missing_params_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PARAMS_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setenv("INPUT_DIR", str(tmp_path))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))

    with pytest.raises(FileNotFoundError):
        Agent(stdout=io.StringIO())


def test_missing_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARAMS_FILE", raising=False)

    with pytest.raises(KeyError):
        Agent(stdout=io.StringIO())


def test_params_file_must_be_dict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    params_file = tmp_path / "params.json"
    params_file.write_text("[1, 2, 3]")  # массив, не объект
    monkeypatch.setenv("PARAMS_FILE", str(params_file))
    monkeypatch.setenv("INPUT_DIR", str(tmp_path))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))

    with pytest.raises(TypeError, match="JSON-объект"):
        Agent(stdout=io.StringIO())


def test_progress_writes_ndjson(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.progress(0.25, "Quarter")

    line = out.getvalue().strip().split("\n")[-1]
    assert "\n" not in line
    payload = json.loads(line)
    assert payload == {"type": "progress", "value": 0.25, "label": "Quarter"}


def test_progress_without_label(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.progress(0.5)

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "progress", "value": 0.5}


def test_progress_value_clamped(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.progress(1.5)
    agent.progress(-0.1)

    lines = out.getvalue().strip().split("\n")
    # [0] = started, [1] = clamped 1.0, [2] = clamped 0.0
    assert json.loads(lines[1])["value"] == 1.0
    assert json.loads(lines[2])["value"] == 0.0


def test_log_writes_ndjson(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.log("info", "started processing")

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "log", "level": "info", "msg": "started processing"}


def test_log_invalid_level_raises(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    with pytest.raises(ValueError):
        agent.log("YELL", "msg")


def test_item_done(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.item_done("01", summary="ok", data={"verdict": "approve"})

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload["type"] == "item_done"
    assert payload["id"] == "01"
    assert payload["summary"] == "ok"
    assert payload["data"] == {"verdict": "approve"}


def test_item_done_minimal(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.item_done("02")

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "item_done", "id": "02"}


def test_error_event(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.error(item_id="03", msg="нет файла презентации", retryable=False)

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "error", "id": "03", "msg": "нет файла презентации", "retryable": False}


def test_started_event_at_init(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    Agent(stdout=out)

    line = out.getvalue().strip()
    payload = json.loads(line)
    assert payload["type"] == "started"
    assert "ts" in payload
