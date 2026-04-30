"""Тесты публичного API класса Agent."""
# ruff: noqa: RUF002
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

    agent.error("нет файла презентации", item_id="03", retryable=False)

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "error", "id": "03", "msg": "нет файла презентации", "retryable": False}


def test_started_event_at_init(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    Agent(stdout=out)

    line = out.getvalue().strip().split("\n")[0]
    payload = json.loads(line)
    assert payload["type"] == "started"
    assert "ts" in payload


def test_error_without_item_id(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.error("global crash")

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "error", "msg": "global crash", "retryable": True}


def test_result_event(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    # имитируем что агент написал артефакты
    (agent.output_dir / "report.docx").write_bytes(b"fake docx")
    (agent.output_dir / "summary.json").write_text("{}")

    agent.result(artifacts=[
        {"id": "report", "path": "report.docx"},
        {"id": "summary", "path": "summary.json"},
    ])

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload["type"] == "result"
    assert len(payload["artifacts"]) == 2
    assert payload["artifacts"][0]["id"] == "report"


def test_result_artifact_path_must_exist(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    with pytest.raises(FileNotFoundError) as exc:
        agent.result(artifacts=[{"id": "report", "path": "nonexistent.docx"}])

    assert "nonexistent" in str(exc.value)


def test_double_result_raises(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())
    (agent.output_dir / "x.txt").write_text("x")

    agent.result(artifacts=[{"id": "x", "path": "x.txt"}])

    with pytest.raises(RuntimeError):
        agent.result(artifacts=[{"id": "x", "path": "x.txt"}])


def test_failed_event(setup_env: dict[str, Path]) -> None:
    out = io.StringIO()
    agent = Agent(stdout=out)

    agent.failed("crashed", details="traceback...")

    payload = json.loads(out.getvalue().strip().split("\n")[-1])
    assert payload == {"type": "failed", "msg": "crashed", "details": "traceback..."}


def test_failed_blocks_subsequent_calls(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())
    agent.failed("oops")

    with pytest.raises(RuntimeError):
        agent.progress(0.5)


def test_progress_after_result_raises(setup_env: dict[str, Path]) -> None:
    """Любой метод после result даёт RuntimeError."""
    agent = Agent(stdout=io.StringIO())
    (agent.output_dir / "x.txt").write_text("x")
    agent.result(artifacts=[{"id": "x", "path": "x.txt"}])

    with pytest.raises(RuntimeError):
        agent.log("info", "после result нельзя")
    with pytest.raises(RuntimeError):
        agent.item_done("y")
    with pytest.raises(RuntimeError):
        agent.error("крах")


def test_result_rejects_path_traversal(setup_env: dict[str, Path], tmp_path: Path) -> None:
    """result() не должен разрешать путь вне output_dir."""
    agent = Agent(stdout=io.StringIO())
    # создаём файл вне output_dir но внутри tmp_path
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")

    with pytest.raises(ValueError, match="выходит за пределы"):
        agent.result(artifacts=[{"id": "x", "path": "../secret.txt"}])


def test_result_empty_artifacts_rejected(setup_env: dict[str, Path]) -> None:
    agent = Agent(stdout=io.StringIO())

    with pytest.raises(ValueError, match="пустым списком"):
        agent.result(artifacts=[])


def test_result_rejects_absolute_path(setup_env: dict[str, Path]) -> None:
    """Абсолютный path в artifacts — ошибка с понятным сообщением, не тихий пропуск."""
    agent = Agent(stdout=io.StringIO())
    (agent.output_dir / "echo.docx").write_text("x")

    with pytest.raises(ValueError, match="относительным"):
        agent.result(artifacts=[{"id": "report", "path": str(agent.output_dir / "echo.docx")}])


def test_env_is_read_only(setup_env: dict[str, Path]) -> None:
    """Студент не должен случайно мутировать env родительского процесса через agent.env."""
    agent = Agent(stdout=io.StringIO())
    with pytest.raises(TypeError):
        agent.env["NEW_KEY"] = "value"  # type: ignore[index]


def test_item_done_non_json_serializable_data(setup_env: dict[str, Path]) -> None:
    """Не-JSON-сериализуемое значение в data → TypeError с понятным сообщением."""

    class _CustomObject:
        pass

    agent = Agent(stdout=io.StringIO())
    with pytest.raises(TypeError, match="JSON-сериализуем"):
        agent.item_done("01", data={"obj": _CustomObject()})
