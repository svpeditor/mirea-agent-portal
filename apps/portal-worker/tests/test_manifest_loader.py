"""builder/manifest_loader.py — парсинг и валидация."""
from pathlib import Path

import pytest


def write_manifest(dir_: Path, content: str) -> Path:
    p = dir_ / "manifest.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _good_manifest(agent_id: str = "test", base_image: str = "python:3.12-slim") -> str:
    return f"""
id: {agent_id}
name: "Test"
version: "0.1.0"
category: "научная-работа"
short_description: "test"
inputs: {{}}
files: {{}}
outputs:
  - id: out
    type: any
    label: out
    filename: out.txt
runtime:
  docker:
    base_image: "{base_image}"
    setup: []
    entrypoint: ["python", "agent.py"]
  llm:
    provider: openrouter
    models: []
  limits:
    max_runtime_minutes: 1
    max_memory_mb: 128
    max_cpu_cores: 1
"""


def test_loads_valid_manifest(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    write_manifest(tmp_path, _good_manifest())
    manifest = load_and_validate_manifest(
        repo_dir=tmp_path, agent_slug="test",
        allowed_base_images=["python:3.12-slim"],
    )
    assert manifest.id == "test"
    assert manifest.runtime.docker.base_image == "python:3.12-slim"


def test_no_manifest_file_raises(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    from portal_worker.core.exceptions import BuildError
    with pytest.raises(BuildError) as exc:
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="x",
            allowed_base_images=["python:3.12-slim"],
        )
    assert exc.value.code == "manifest_not_found"


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    from portal_worker.core.exceptions import BuildError
    write_manifest(tmp_path, "id: [unclosed")
    with pytest.raises(BuildError) as exc:
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="x",
            allowed_base_images=["python:3.12-slim"],
        )
    assert exc.value.code == "manifest_invalid"


def test_pydantic_validation_fails(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    from portal_worker.core.exceptions import BuildError
    write_manifest(tmp_path, "id: x\nname: ''")
    with pytest.raises(BuildError) as exc:
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="x",
            allowed_base_images=["python:3.12-slim"],
        )
    assert exc.value.code == "manifest_invalid"


def test_slug_mismatch_raises(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    from portal_worker.core.exceptions import BuildError
    write_manifest(tmp_path, _good_manifest(agent_id="actual-id"))
    with pytest.raises(BuildError) as exc:
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="different-id",
            allowed_base_images=["python:3.12-slim"],
        )
    assert exc.value.code == "manifest_invalid"
    assert "id_mismatch" in exc.value.log


def test_disallowed_base_image_raises(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    from portal_worker.core.exceptions import BuildError
    write_manifest(tmp_path, _good_manifest(base_image="ubuntu:22.04"))
    with pytest.raises(BuildError) as exc:
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="test",
            allowed_base_images=["python:3.12-slim"],
        )
    assert exc.value.code == "base_image_not_allowed"


def test_returns_pydantic_model(tmp_path: Path) -> None:
    from portal_sdk.manifest import Manifest

    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    write_manifest(tmp_path, _good_manifest())
    m = load_and_validate_manifest(
        repo_dir=tmp_path, agent_slug="test",
        allowed_base_images=["python:3.12-slim"],
    )
    assert isinstance(m, Manifest)


def test_accepts_all_three_python_versions(tmp_path: Path) -> None:
    from portal_worker.builder.manifest_loader import load_and_validate_manifest
    for img in ["python:3.11-slim", "python:3.12-slim", "python:3.13-slim"]:
        d = tmp_path / img.replace(":", "_")
        d.mkdir()
        write_manifest(d, _good_manifest(base_image=img))
        m = load_and_validate_manifest(
            repo_dir=d, agent_slug="test",
            allowed_base_images=["python:3.11-slim", "python:3.12-slim", "python:3.13-slim"],
        )
        assert m.runtime.docker.base_image == img
