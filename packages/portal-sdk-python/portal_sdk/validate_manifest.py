"""CLI: portal-sdk-validate-manifest <agent_dir>.

Проверяет manifest.yaml в указанной папке. Вылетает с exit-кодом 1 при
ошибке, печатает осмысленные сообщения. Используется студентами
НУГ перед commit'ом, может быть подключено в pre-commit / CI.
"""
# ruff: noqa: RUF001, RUF002, RUF003
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from portal_sdk.manifest import Manifest


def validate(agent_dir: Path) -> tuple[bool, str]:
    """Вернуть (ok, message). ok=False означает ошибку — message для печати."""
    manifest_path = agent_dir / "manifest.yaml"
    if not manifest_path.is_file():
        return False, f"manifest.yaml не найден в {agent_dir.resolve()}"
    try:
        manifest = Manifest.from_yaml(manifest_path)
    except ValidationError as exc:
        # Pydantic v2 — формируем человеко-читаемый отчёт
        lines = [f"Не валиден manifest.yaml ({manifest_path.resolve()}):"]
        for err in exc.errors():
            loc = ".".join(str(x) for x in err["loc"]) or "<root>"
            lines.append(f"  {loc}: {err['msg']}")
        return False, "\n".join(lines)
    except Exception as exc:
        return False, f"Ошибка чтения manifest.yaml: {exc}"

    # Доп. проверки: agent.py существует если entrypoint начинается с python
    entrypoint = manifest.runtime.docker.entrypoint
    if entrypoint and entrypoint[0] in ("python", "python3") and len(entrypoint) > 1:
        script = agent_dir / entrypoint[1]
        if not script.is_file():
            return False, (
                f"runtime.docker.entrypoint указывает на {entrypoint[1]!r}, "
                f"но файл {script.resolve()} не найден"
            )

    summary = (
        f"manifest.yaml ok\n"
        f"  id:       {manifest.id}\n"
        f"  name:     {manifest.name}\n"
        f"  version:  {manifest.version}\n"
        f"  category: {manifest.category}\n"
        f"  inputs:   {len(manifest.inputs)}\n"
        f"  files:    {len(manifest.files)}\n"
        f"  outputs:  {len(manifest.outputs)}\n"
        f"  llm:      {'да' if manifest.runtime.llm else 'нет'}"
    )
    return True, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="portal-sdk-validate-manifest",
        description="Проверка manifest.yaml на соответствие контракту v0.1.",
    )
    parser.add_argument(
        "agent_dir",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Папка с manifest.yaml (по умолчанию — текущая)",
    )
    args = parser.parse_args()

    ok, msg = validate(args.agent_dir)
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
