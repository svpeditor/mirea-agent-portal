"""Регенерация docs/manifest.schema.json.

Запускать вручную после правок в `portal_sdk/manifest.py`:

    python packages/portal-sdk-python/scripts/gen_manifest_schema.py

Генерит JSON Schema из Pydantic-модели Manifest и сохраняет в
docs/manifest.schema.json. Файл подключается в студенческих agent-репо
через комментарий-директиву vscode-yaml:

    # yaml-language-server: $schema=https://raw.githubusercontent.com/svpeditor/mirea-agent-portal/main/docs/manifest.schema.json
"""
from __future__ import annotations

import json
from pathlib import Path

from portal_sdk.manifest import Manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "docs" / "manifest.schema.json"


def main() -> None:
    schema = Manifest.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Portal Agent Manifest v0.1"
    schema["description"] = (
        "Манифест агента платформы AI-агентов МИРЭА. "
        "Контракт v0.1 (см. docs/contract.md)."
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
