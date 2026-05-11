"""Тесты CLI portal-sdk-validate-manifest."""
# ruff: noqa: RUF001, RUF002
from __future__ import annotations

import shutil
from pathlib import Path

from portal_sdk.validate_manifest import validate


def test_validate_dummy_agent_ok(fixtures_dir: Path) -> None:
    ok, msg = validate(fixtures_dir / "dummy_agent")
    assert ok, msg
    assert "manifest.yaml ok" in msg
    assert "id:" in msg
    assert "outputs:" in msg


def test_validate_missing_manifest(tmp_path: Path) -> None:
    ok, msg = validate(tmp_path)
    assert not ok
    assert "manifest.yaml не найден" in msg


def test_validate_invalid_no_id(fixtures_dir: Path, tmp_path: Path) -> None:
    """Невалидный manifest даёт ok=False и осмысленную ошибку."""
    src = fixtures_dir / "invalid_manifests" / "no_id.yaml"
    dst = tmp_path / "manifest.yaml"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    ok, msg = validate(tmp_path)
    assert not ok
    assert "Не валиден manifest.yaml" in msg
    assert "id" in msg.lower()


def test_validate_invalid_duplicate_outputs(fixtures_dir: Path, tmp_path: Path) -> None:
    src = fixtures_dir / "invalid_manifests" / "duplicate_output_ids.yaml"
    dst = tmp_path / "manifest.yaml"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    ok, msg = validate(tmp_path)
    assert not ok
    assert "outputs" in msg


def test_validate_entrypoint_script_missing(fixtures_dir: Path, tmp_path: Path) -> None:
    """Если manifest указывает entrypoint=python <script>, а скрипта нет — error."""
    src_manifest = fixtures_dir / "dummy_agent" / "manifest.yaml"
    (tmp_path / "manifest.yaml").write_text(src_manifest.read_text(encoding="utf-8"), encoding="utf-8")
    # умышленно не копируем agent.py
    ok, msg = validate(tmp_path)
    assert not ok
    assert "agent.py" in msg


def test_validate_entrypoint_script_present(fixtures_dir: Path, tmp_path: Path) -> None:
    """С agent.py всё проходит."""
    shutil.copytree(fixtures_dir / "dummy_agent", tmp_path / "agent")
    ok, msg = validate(tmp_path / "agent")
    assert ok, msg


def test_validate_repo_echo_agent() -> None:
    """Sanity: agents/echo в монорепо валидируется."""
    repo_root = Path(__file__).resolve().parents[3]
    echo = repo_root / "agents" / "echo"
    if not echo.is_dir():
        return  # запуск вне монорепо
    ok, msg = validate(echo)
    assert ok, msg
