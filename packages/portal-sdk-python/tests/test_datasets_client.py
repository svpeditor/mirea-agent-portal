"""Юнит-тесты DatasetClient: резолв base_url/token из env + сборка URL."""
from __future__ import annotations

import pytest

from portal_sdk.datasets import (
    DatasetClient,
    DatasetError,
    _resolve_base_url,
    _resolve_token,
)


def test_base_from_portal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTAL_API_BASE_URL", "http://api:8000/")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    assert _resolve_base_url() == "http://api:8000"


def test_base_fallback_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTAL_API_BASE_URL", raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "http://api:8000/llm/v1")
    assert _resolve_base_url() == "http://api:8000"


def test_base_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTAL_API_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    with pytest.raises(DatasetError):
        _resolve_base_url()


def test_token_fallback_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTAL_AGENT_TOKEN", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "por-job-abc")
    assert _resolve_token() == "por-job-abc"


def test_token_prefers_portal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTAL_AGENT_TOKEN", "por-job-portal")
    monkeypatch.setenv("OPENROUTER_API_KEY", "por-job-openrouter")
    assert _resolve_token() == "por-job-portal"


def test_token_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTAL_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(DatasetError):
        _resolve_token()


def test_client_root_built() -> None:
    c = DatasetClient("math-tasks", base_url="http://api:8000/", token="t")
    assert c._root == "http://api:8000/api/sandbox/datasets/math-tasks"
    assert c._headers == {"Authorization": "Bearer t"}


def test_put_requires_payload() -> None:
    c = DatasetClient("x", base_url="http://api:8000", token="t")
    with pytest.raises(ValueError):
        c.put("k")
