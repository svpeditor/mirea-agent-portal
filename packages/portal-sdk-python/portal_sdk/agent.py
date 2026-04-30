# packages/portal-sdk-python/portal_sdk/agent.py
"""Публичный API SDK — класс Agent."""
from __future__ import annotations

import json
import os
import sys
from collections.abc import MutableMapping
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from pydantic import BaseModel

from portal_sdk.events import (
    ErrorEvent,
    ItemDoneEvent,
    LogEvent,
    LogLevel,
    ProgressEvent,
    StartedEvent,
)


class Agent:
    """Обёртка над контрактом портала.

    Читает $PARAMS_FILE, $INPUT_DIR, $OUTPUT_DIR из env при инициализации.
    Автоматически отправляет событие `started`; все события — NDJSON в stdout.
    """

    def __init__(self, stdout: IO[str] | None = None) -> None:
        self._stdout = stdout if stdout is not None else sys.stdout
        self._finished = False

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

        raw = json.loads(params_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(
                f"PARAMS_FILE должен содержать JSON-объект, получен {type(raw).__name__}."
            )
        self._params: dict[str, Any] = raw

        # Сразу публикуем started
        self._emit(StartedEvent(ts=datetime.now(UTC).isoformat()))

    # --- Свойства ---

    @property
    def params(self) -> dict[str, Any]:
        return self._params

    def input_dir(self, input_id: str) -> Path:
        path = self._input_dir / input_id
        if not path.exists():
            raise FileNotFoundError(
                f"Input '{input_id}' не найден в {self._input_dir}. "
                f"Проверь, что в manifest.yaml есть files.{input_id}."
            )
        return path

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    @property
    def env(self) -> MutableMapping[str, str]:
        return os.environ

    # --- События прогресса ---

    def progress(self, value: float, label: str | None = None) -> None:
        """Числовой прогресс 0..1 + опциональная подпись."""
        clamped = max(0.0, min(1.0, value))
        self._emit(ProgressEvent(value=clamped, label=label))

    def log(self, level: str, msg: str) -> None:
        """Сообщение в общую ленту задачи. level: debug|info|warn|error."""
        self._emit(LogEvent(level=LogLevel(level), msg=msg))

    def item_done(
        self,
        item_id: str,
        summary: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Завершение одного элемента в серии (например, одной работы из 46)."""
        self._emit(ItemDoneEvent(id=item_id, summary=summary, data=data))

    def error(self, msg: str, item_id: str | None = None, retryable: bool = True) -> None:
        """Нефатальная ошибка по конкретному элементу. Агент продолжает."""
        self._emit(ErrorEvent(id=item_id, msg=msg, retryable=retryable))

    # --- Внутреннее ---

    def _emit(self, event: BaseModel) -> None:
        line = event.model_dump_json(exclude_none=True)
        self._stdout.write(line + "\n")
        self._stdout.flush()
