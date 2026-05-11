"""Manifest validation для proverka_stub."""
from __future__ import annotations

from pathlib import Path

from portal_sdk.manifest import Manifest

MANIFEST = Path(__file__).resolve().parent.parent / "manifest.yaml"


def test_manifest_parses() -> None:
    m = Manifest.from_yaml(MANIFEST)
    assert m.id == "proverka"
    assert m.version == "0.1.0"
    assert m.category == "научная-работа"


def test_manifest_outputs() -> None:
    m = Manifest.from_yaml(MANIFEST)
    ids = {o.id for o in m.outputs}
    assert ids == {"report", "per_work"}
    primaries = [o.id for o in m.outputs if o.primary]
    assert primaries == ["report"]


def test_manifest_files_works_folder() -> None:
    m = Manifest.from_yaml(MANIFEST)
    assert "works" in m.files
    works = m.files["works"]
    assert works.type == "folder"
    assert works.required is True
    assert ".pdf" in works.accept
    assert ".docx" in works.accept


def test_manifest_inputs_grade_level() -> None:
    m = Manifest.from_yaml(MANIFEST)
    grade = m.inputs["grade_level"]
    assert grade.type == "select"
    assert {opt.value for opt in grade.options} == {"5-7", "8-9", "10-11"}
