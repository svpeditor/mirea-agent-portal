"""manifest_loader валидация runtime.llm: provider, non-empty models, global whitelist."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from portal_worker.builder.manifest_loader import load_and_validate_manifest
from portal_worker.core.exceptions import BuildError


def _write_manifest(tmp_path: Path, raw: dict) -> Path:
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return tmp_path


@pytest.fixture
def base_manifest() -> dict:
    return {
        "id": "test-agent",
        "name": "T",
        "version": "0.1.0",
        "category": "научная-работа",
        "short_description": "x",
        "outputs": [{"id": "r", "type": "json", "label": "R", "filename": "r.json"}],
        "runtime": {
            "docker": {
                "base_image": "python:3.12-slim",
                "entrypoint": ["python", "agent.py"],
            },
            "limits": {"max_runtime_minutes": 5, "max_memory_mb": 256, "max_cpu_cores": 1},
        },
    }


def test_llm_provider_must_be_openrouter(tmp_path, base_manifest):
    base_manifest["runtime"]["llm"] = {"provider": "anthropic", "models": ["claude-haiku"]}
    _write_manifest(tmp_path, base_manifest)
    with pytest.raises(BuildError) as ei:
        load_and_validate_manifest(
            repo_dir=tmp_path,
            agent_slug="test-agent",
            allowed_base_images=["python:3.12-slim"],
            allowed_llm_models=["anthropic/claude-haiku-4-5"],
        )
    assert "openrouter" in str(ei.value).lower() or "provider" in str(ei.value).lower()


def test_llm_models_must_be_non_empty(tmp_path, base_manifest):
    base_manifest["runtime"]["llm"] = {"provider": "openrouter", "models": []}
    _write_manifest(tmp_path, base_manifest)
    with pytest.raises(BuildError):
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="test-agent",
            allowed_base_images=["python:3.12-slim"],
            allowed_llm_models=["anthropic/claude-haiku-4-5"],
        )


def test_llm_model_must_be_in_global_whitelist(tmp_path, base_manifest):
    base_manifest["runtime"]["llm"] = {
        "provider": "openrouter",
        "models": ["anthropic/claude-opus-99"],
    }
    _write_manifest(tmp_path, base_manifest)
    with pytest.raises(BuildError) as ei:
        load_and_validate_manifest(
            repo_dir=tmp_path, agent_slug="test-agent",
            allowed_base_images=["python:3.12-slim"],
            allowed_llm_models=["deepseek/deepseek-chat", "anthropic/claude-haiku-4-5"],
        )
    assert "whitelist" in str(ei.value).lower() or "not_allowed" in str(ei.value).lower()


def test_llm_valid(tmp_path, base_manifest):
    base_manifest["runtime"]["llm"] = {
        "provider": "openrouter",
        "models": ["deepseek/deepseek-chat"],
    }
    _write_manifest(tmp_path, base_manifest)
    m = load_and_validate_manifest(
        repo_dir=tmp_path, agent_slug="test-agent",
        allowed_base_images=["python:3.12-slim"],
        allowed_llm_models=["deepseek/deepseek-chat"],
    )
    assert m.runtime.llm.provider == "openrouter"
    assert m.runtime.llm.models == ["deepseek/deepseek-chat"]


def test_no_llm_section_is_valid(tmp_path, base_manifest):
    """Агент без LLM — manifest валиден, allowed_llm_models не нужен."""
    _write_manifest(tmp_path, base_manifest)
    m = load_and_validate_manifest(
        repo_dir=tmp_path, agent_slug="test-agent",
        allowed_base_images=["python:3.12-slim"],
        allowed_llm_models=[],
    )
    assert m.runtime.llm is None
