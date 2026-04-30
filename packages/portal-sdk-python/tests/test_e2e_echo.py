"""End-to-end: реальный echo-агент работает через local_runner."""
# ruff: noqa: RUF003
import io
import json
from pathlib import Path

from portal_sdk.local_runner import run


def test_echo_agent_e2e(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[3]
    echo_dir = repo_root / "agents" / "echo"
    assert (echo_dir / "manifest.yaml").exists(), "agents/echo не найден — структура моно-репо сломана"

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    log = io.StringIO()
    exit_code = run(
        agent_dir=echo_dir,
        params={"message": "ПРИВЕТ", "loops": 3, "shout": False},
        files={},
        output_dir=output_dir,
        log=log,
    )

    assert exit_code == 0, f"echo-агент упал. Лог:\n{log.getvalue()}"

    # docx должен появиться
    assert (output_dir / "echo.docx").is_file()
    assert (output_dir / "echo.docx").stat().st_size > 0

    # summary.json должен отражать параметры
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary == {"message": "ПРИВЕТ", "loops": 3, "shout": False}

    # В лог попали ключевые события
    log_text = log.getvalue()
    assert '"type":"started"' in log_text
    assert '"type":"progress"' in log_text
    assert '"type":"item_done"' in log_text
    assert '"type":"result"' in log_text
