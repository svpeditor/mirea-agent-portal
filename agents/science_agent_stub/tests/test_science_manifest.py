"""Manifest validation для science_agent_stub."""
from __future__ import annotations

from pathlib import Path

from portal_sdk.manifest import Manifest

MANIFEST = Path(__file__).resolve().parent.parent / "manifest.yaml"


def test_manifest_parses() -> None:
    m = Manifest.from_yaml(MANIFEST)
    assert m.id == "science-agent"
    assert m.version == "0.1.0"


def test_manifest_inputs_topic_textarea() -> None:
    m = Manifest.from_yaml(MANIFEST)
    topic = m.inputs["topic"]
    assert topic.type == "textarea"
    assert topic.required is True


def test_manifest_inputs_language_radio() -> None:
    m = Manifest.from_yaml(MANIFEST)
    lang = m.inputs["language"]
    assert lang.type == "radio"
    assert {opt.value for opt in lang.options} == {"ru", "en"}


def test_manifest_outputs_report_primary() -> None:
    m = Manifest.from_yaml(MANIFEST)
    primary = [o for o in m.outputs if o.primary]
    assert len(primary) == 1
    assert primary[0].id == "report"


def test_manifest_runtime_llm_configured() -> None:
    m = Manifest.from_yaml(MANIFEST)
    assert m.runtime.llm is not None
    assert m.runtime.llm.provider == "openrouter"
    assert "deepseek/deepseek-r1" in m.runtime.llm.models
