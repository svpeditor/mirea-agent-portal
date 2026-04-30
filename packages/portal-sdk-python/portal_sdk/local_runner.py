"""Локальный запуск агента — для разработки агентов без портала.

Эмулирует то, что портал делает в проде:
- готовит $PARAMS_FILE, $INPUT_DIR, $OUTPUT_DIR
- запускает agent.py как subprocess
- стримит stdout/stderr на экран
"""
# ruff: noqa: RUF001, RUF002, RUF003
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import IO

from portal_sdk.manifest import Manifest


def run(
    agent_dir: Path,
    params: dict[str, object],
    files: dict[str, Path],
    output_dir: Path,
    log: IO[str] | None = None,
    python_executable: str | None = None,
) -> int:
    """Запустить агента локально.  # noqa: RUF002

    agent_dir — папка с manifest.yaml и agent.py
    params — словарь, который окажется в $PARAMS_FILE
    files — {input_id: path_to_folder_or_file}, копируются в $INPUT_DIR/<input_id>
    output_dir — куда агент будет складывать артефакты (должна существовать)
    log — куда писать stdout/stderr субпроцесса (по умолчанию sys.stderr)
    python_executable — какой Python запустить (по умолчанию sys.executable)

    Возвращает exit-код процесса агента.
    """
    if log is None:
        log = sys.stderr

    # Валидируем манифест перед запуском — раньше упадём, если что не так
    manifest = Manifest.from_yaml(agent_dir / "manifest.yaml")

    # Готовим временные input/params файлы рядом с output_dir, чтобы всё видно
    workspace = output_dir.parent / f"{output_dir.name}.workspace"
    workspace.mkdir(exist_ok=True)
    input_dir = workspace / "input"
    input_dir.mkdir(exist_ok=True)
    params_file = workspace / "params.json"

    params_file.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")

    # Копируем файлы пользователя в $INPUT_DIR/<input_id>/
    for input_id, src in files.items():
        target = input_dir / input_id
        if target.exists():
            shutil.rmtree(target)
        if src.is_dir():
            shutil.copytree(src, target)
        else:
            target.mkdir()
            shutil.copy2(src, target / src.name)

    # Готовим env как в проде
    child_env = os.environ.copy()
    child_env["PARAMS_FILE"] = str(params_file)
    child_env["INPUT_DIR"] = str(input_dir)
    child_env["OUTPUT_DIR"] = str(output_dir)
    child_env.setdefault("OPENROUTER_API_KEY", child_env.get("OPENROUTER_API_KEY", "MISSING"))
    child_env.setdefault("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    python = python_executable or sys.executable
    entrypoint = manifest.runtime.docker.entrypoint
    # Если entrypoint начинается с "python" — заменяем на текущий sys.executable
    # (чтобы subprocess наследовал тот же venv с установленным portal_sdk)
    if entrypoint and entrypoint[0] in ("python", "python3"):
        cmd = [python, *entrypoint[1:]]
    else:
        cmd = list(entrypoint)

    log.write(f"[local-runner] cd {agent_dir}\n")
    log.write(f"[local-runner] $ {' '.join(cmd)}\n")
    log.write(f"[local-runner] PARAMS_FILE={params_file}\n")
    log.write(f"[local-runner] INPUT_DIR={input_dir}\n")
    log.write(f"[local-runner] OUTPUT_DIR={output_dir}\n")
    log.flush()

    proc = subprocess.run(
        cmd,
        cwd=agent_dir,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )

    log.write("--- stdout (NDJSON events) ---\n")
    log.write(proc.stdout)
    log.write("--- stderr ---\n")
    log.write(proc.stderr)
    log.flush()

    return proc.returncode


def main() -> None:
    """CLI: portal-sdk-run-local <agent_dir>"""
    parser = argparse.ArgumentParser(
        prog="portal-sdk-run-local",
        description="Запустить агента локально без портала.",
    )
    parser.add_argument(
        "agent_dir", type=Path, help="Папка с manifest.yaml и agent.py"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("./_local_output"),
        help="Куда сложить артефакты (по умолчанию ./_local_output)",
    )
    args = parser.parse_args()

    manifest = Manifest.from_yaml(args.agent_dir / "manifest.yaml")
    print(f"Агент: {manifest.name} v{manifest.version}")
    print(f"Категория: {manifest.category}")
    print()

    # Запрашиваем параметры
    params: dict[str, object] = {}
    for key, field in manifest.inputs.items():
        prompt_text = f"  {field.label}"
        default = getattr(field, "default", None)
        if default is not None:
            prompt_text += f" [{default}]"
        prompt_text += ": "
        raw = input(prompt_text).strip()
        if not raw and default is not None:
            params[key] = default
        elif field.type.value == "checkbox":
            params[key] = raw.lower() in ("y", "yes", "true", "1", "да")
        elif field.type.value == "number":
            params[key] = float(raw)
        else:
            params[key] = raw

    # Запрашиваем пути к файлам
    files: dict[str, Path] = {}
    for input_id, file_field in manifest.files.items():
        path_raw = input(f"  Путь к '{file_field.label}': ").strip()
        if path_raw:
            files[input_id] = Path(path_raw).expanduser().resolve()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print()
    exit_code = run(
        agent_dir=args.agent_dir,
        params=params,
        files=files,
        output_dir=args.output_dir,
    )

    print()
    if exit_code == 0:
        print(f"Готово. Артефакты: {args.output_dir}")
    else:
        print(f"Агент завершился с кодом {exit_code}")
    sys.exit(exit_code)
