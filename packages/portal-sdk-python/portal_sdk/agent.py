"""Публичный API SDK — класс Agent."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import IO, Any


class Agent:
    """Обёртка над контрактом портала.

    Читает $PARAMS_FILE, $INPUT_DIR, $OUTPUT_DIR из env при инициализации.
    Пишет события в stdout как NDJSON. По умолчанию stdout = sys.stdout,
    но в тестах можно подменить.
    """

    def __init__(self, stdout: IO[str] | None = None) -> None:
        self._stdout = stdout if stdout is not None else sys.stdout
        self._finished = False

        # Обязательные env
        try:
            params_file = Path(os.environ["PARAMS_FILE"])
            self._input_dir = Path(os.environ["INPUT_DIR"])
            self._output_dir = Path(os.environ["OUTPUT_DIR"])
        except KeyError as e:
            raise KeyError(
                f"Обязательная env-переменная не установлена: {e}. "
                "Если ты разрабатываешь агента локально — используй `portal-sdk-run-local`."
            ) from None

        if not params_file.is_file():
            raise FileNotFoundError(f"PARAMS_FILE не найден: {params_file}")

        self._params: dict[str, Any] = json.loads(params_file.read_text(encoding="utf-8"))

    @property
    def params(self) -> dict[str, Any]:
        """Параметры формы, заданные пользователем."""
        return self._params

    def input_dir(self, input_id: str) -> Path:
        """Путь к bind-mount директории для input из manifest.yaml."""
        path = self._input_dir / input_id
        if not path.exists():
            raise FileNotFoundError(
                f"Input '{input_id}' не найден в {self._input_dir}. "
                f"Проверь, что в manifest.yaml есть files.{input_id}."
            )
        return path

    @property
    def output_dir(self) -> Path:
        """Директория, куда агент кладёт артефакты-результаты."""
        return self._output_dir

    @property
    def env(self) -> os._Environ[str]:
        """Прокси к os.environ — для чтения OPENROUTER_API_KEY и других."""
        return os.environ
