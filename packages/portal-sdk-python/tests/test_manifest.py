"""Тесты загрузки и валидации manifest.yaml."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from portal_sdk.manifest import (
    CategoryStrict,
    CheckboxField,
    FolderFile,
    Manifest,
    OutputType,
    TextField,
)


def test_load_proverka_manifest(fixtures_dir: Path) -> None:
    manifest = Manifest.from_yaml(fixtures_dir / "proverka_manifest.yaml")

    assert manifest.id == "school-works-expert"
    assert manifest.version == "1.0.0"
    assert manifest.category == "научная-работа"
    assert manifest.icon == "🎓"


def test_input_fields_parsed(fixtures_dir: Path) -> None:
    manifest = Manifest.from_yaml(fixtures_dir / "proverka_manifest.yaml")

    section = manifest.inputs["section"]
    assert isinstance(section, TextField)
    assert section.label == "Секция конкурса"
    assert section.default == "общая"
    assert section.required is True

    strict = manifest.inputs["strict_mode"]
    assert isinstance(strict, CheckboxField)
    assert strict.default is False


def test_files_parsed(fixtures_dir: Path) -> None:
    manifest = Manifest.from_yaml(fixtures_dir / "proverka_manifest.yaml")

    works = manifest.files["works_folder"]
    assert isinstance(works, FolderFile)
    assert works.accept == [".docx", ".pdf", ".pptx"]
    assert works.max_total_size_mb == 500


def test_outputs_parsed(fixtures_dir: Path) -> None:
    manifest = Manifest.from_yaml(fixtures_dir / "proverka_manifest.yaml")

    assert len(manifest.outputs) == 2
    report = manifest.outputs[0]
    assert report.id == "report"
    assert report.type == OutputType.DOCX
    assert report.primary is True


def test_runtime_limits(fixtures_dir: Path) -> None:
    manifest = Manifest.from_yaml(fixtures_dir / "proverka_manifest.yaml")

    assert manifest.runtime.limits.max_runtime_minutes == 60
    assert manifest.runtime.limits.max_memory_mb == 1024
    assert manifest.runtime.llm.models == ["deepseek/deepseek-chat"]


def test_missing_id_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValidationError) as exc:
        Manifest.from_yaml(fixtures_dir / "invalid_manifests" / "no_id.yaml")

    assert "id" in str(exc.value).lower()


def test_unknown_input_type_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValidationError):
        Manifest.from_yaml(fixtures_dir / "invalid_manifests" / "bad_input_type.yaml")


def test_category_known_becomes_enum(fixtures_dir: Path) -> None:
    manifest = Manifest.from_yaml(fixtures_dir / "proverka_manifest.yaml")

    assert isinstance(manifest.category, CategoryStrict)
    assert manifest.category == CategoryStrict.SCIENCE


def test_category_unknown_stays_str() -> None:
    data = {
        "id": "my-agent",
        "name": "Агент",
        "version": "1.0.0",
        "category": "моя-кастомная",
        "short_description": "Описание",
        "runtime": {
            "docker": {
                "base_image": "python:3.12-slim",
                "entrypoint": ["python", "run.py"],
            }
        },
    }
    manifest = Manifest.model_validate(data)

    assert isinstance(manifest.category, str)
    assert not isinstance(manifest.category, CategoryStrict)
    assert manifest.category == "моя-кастомная"


def test_duplicate_output_ids_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValidationError) as exc:
        Manifest.from_yaml(fixtures_dir / "invalid_manifests" / "duplicate_output_ids.yaml")

    assert "дубли" in str(exc.value).lower()


def test_two_primaries_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValidationError) as exc:
        Manifest.from_yaml(fixtures_dir / "invalid_manifests" / "two_primaries.yaml")

    assert "primary" in str(exc.value).lower()
