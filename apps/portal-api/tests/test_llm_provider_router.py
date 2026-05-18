"""Unit-тесты резолвера upstream-цели (без БД/сети)."""
from __future__ import annotations

from portal_api.services.llm_provider_router import resolve
from portal_api.services.llm_settings_service import ResolvedLlm


def _r(mode: str, keys: dict | None = None) -> ResolvedLlm:
    return ResolvedLlm(
        openrouter_api_key="OR-KEY",
        openrouter_base_url="https://openrouter.ai/api/v1",
        allowed_models=["openai/gpt-4o"],
        provider_mode=mode,
        provider_keys=keys or {},
    )


def test_openrouter_mode_passthrough() -> None:
    t = resolve("openai/gpt-4o", _r("openrouter", {"openai": "sk-o"}))
    assert t.route == "openrouter"
    assert t.api_key == "OR-KEY"
    assert t.base_url == "https://openrouter.ai/api/v1"
    assert t.upstream_model is None


def test_direct_openai() -> None:
    t = resolve("openai/gpt-4o", _r("direct", {"openai": "sk-openai-xyz"}))
    assert t.route == "direct:openai"
    assert t.base_url == "https://api.openai.com/v1"
    assert t.api_key == "sk-openai-xyz"
    assert t.upstream_model == "gpt-4o"


def test_direct_xai_and_google_strip_prefix() -> None:
    tx = resolve("x-ai/grok-4.3", _r("direct", {"xai": "xai-k"}))
    assert tx.route == "direct:xai"
    assert tx.base_url == "https://api.x.ai/v1"
    assert tx.upstream_model == "grok-4.3"
    tg = resolve("google/gemini-2.5-flash", _r("direct", {"google": "g-k"}))
    assert tg.route == "direct:google"
    assert "generativelanguage.googleapis.com" in tg.base_url
    assert tg.upstream_model == "gemini-2.5-flash"


def test_direct_missing_key_falls_back_to_openrouter() -> None:
    t = resolve("openai/gpt-4o", _r("direct", {"openai": ""}))
    assert t.route == "openrouter"
    assert t.api_key == "OR-KEY"
    assert t.upstream_model is None


def test_direct_anthropic_and_deepseek_stay_openrouter() -> None:
    for m in ("anthropic/claude-opus-4.7", "deepseek/deepseek-r1"):
        t = resolve(m, _r("direct", {"anthropic": "a-k", "deepseek": "d-k"}))
        assert t.route == "openrouter", m
        assert t.upstream_model is None


def test_empty_model_openrouter() -> None:
    assert resolve("", _r("direct", {"openai": "k"})).route == "openrouter"
