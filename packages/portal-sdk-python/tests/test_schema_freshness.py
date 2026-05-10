"""Защищаемся от дрейфа docs/manifest.schema.json: схема в репо должна
совпадать с тем, что генерит scripts/gen_manifest_schema.py.

Если этот тест красный — кто-то поменял Pydantic-модель `Manifest` и
забыл регенерировать схему. Команда: `python packages/portal-sdk-python/
scripts/gen_manifest_schema.py`.
"""
# ruff: noqa: RUF002
from __future__ import annotations

import json
from pathlib import Path

from portal_sdk.manifest import Manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "docs" / "manifest.schema.json"


def test_manifest_schema_in_sync() -> None:
    if not SCHEMA_PATH.is_file():
        # запуск вне монорепо
        return
    fresh = Manifest.model_json_schema()
    fresh["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    fresh["title"] = "Portal Agent Manifest v0.1"
    fresh["description"] = (
        "Манифест агента платформы AI-агентов МИРЭА. "
        "Контракт v0.1 (см. docs/contract.md)."
    )
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Сравниваем через нормализованный JSON — pytest assert на dict
    # ругается на ordered diffs внутри $defs из-за порядка ключей.
    fresh_norm = json.dumps(fresh, sort_keys=True, ensure_ascii=False)
    disk_norm = json.dumps(on_disk, sort_keys=True, ensure_ascii=False)
    assert fresh_norm == disk_norm, (
        "docs/manifest.schema.json устарела. "
        "Запусти: python packages/portal-sdk-python/scripts/gen_manifest_schema.py"
    )
