"""Публичный API SDK — класс Agent."""
# ruff: noqa: RUF001
from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import IO, Any

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticSerializationError

from portal_sdk.events import (
    Artifact,
    ErrorEvent,
    FailedEvent,
    ItemDoneEvent,
    LogEvent,
    LogLevel,
    ProgressEvent,
    ResultEvent,
    StartedEvent,
)

_FINISHED_MSG = "Агент уже завершён (result/failed уже отправлен)."


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
    def env(self) -> Mapping[str, str]:
        """Read-only view на переменные окружения процесса.

        Read-only намеренно: студент не должен случайно мутировать env
        агента через SDK — для этого есть `os.environ` напрямую.
        """
        return MappingProxyType(os.environ)

    # --- События прогресса ---

    def progress(self, value: float, label: str | None = None) -> None:
        """Числовой прогресс 0..1 + опциональная подпись."""
        if self._finished:
            raise RuntimeError(_FINISHED_MSG)
        clamped = max(0.0, min(1.0, value))
        self._emit(ProgressEvent(value=clamped, label=label))

    def log(self, level: str, msg: str) -> None:
        """Сообщение в общую ленту задачи. level: debug|info|warn|error."""
        if self._finished:
            raise RuntimeError(_FINISHED_MSG)
        self._emit(LogEvent(level=LogLevel(level), msg=msg))

    def item_done(
        self,
        item_id: str,
        summary: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Завершение одного элемента в серии (например, одной работы из 46)."""
        if self._finished:
            raise RuntimeError(_FINISHED_MSG)
        self._emit(ItemDoneEvent(id=item_id, summary=summary, data=data))

    def error(self, msg: str, item_id: str | None = None, retryable: bool = True) -> None:
        """Нефатальная ошибка по конкретному элементу. Агент продолжает."""
        if self._finished:
            raise RuntimeError(_FINISHED_MSG)
        self._emit(ErrorEvent(id=item_id, msg=msg, retryable=retryable))

    def result(self, artifacts: list[dict[str, str]]) -> None:
        """Финальное событие успеха.

        artifacts: list[dict] — каждый dict содержит ключи 'id' и 'path'
        (path относительно output_dir). SDK проверяет существование файлов.
        """
        if self._finished:
            raise RuntimeError(_FINISHED_MSG)
        if not artifacts:
            raise ValueError(
                "result() вызван с пустым списком артефактов. "
                "Добавь хотя бы один файл или используй failed() если нечего вернуть."
            )

        normalized = [self._normalize_artifact(a) for a in artifacts]

        # Проверка пути и существования файлов
        for art in normalized:
            # Абсолютные пути запрещены — path должен быть относительным к output_dir
            if Path(art.path).is_absolute():
                raise ValueError(
                    f"Путь артефакта '{art.id}' должен быть относительным к output_dir, "
                    f"получен абсолютный: {art.path!r}. "
                    "Пиши путь как имя файла внутри output_dir, например 'report.docx'."
                )
            full = self._output_dir / art.path
            # Защита от path traversal — путь не должен выходить за output_dir
            try:
                full.resolve().relative_to(self._output_dir.resolve())
            except ValueError:
                raise ValueError(
                    f"Путь артефакта '{art.id}' выходит за пределы output_dir: {art.path!r}. "
                    "Укажи путь относительно output_dir без '..'."
                ) from None
            if not full.is_file():
                raise FileNotFoundError(
                    f"Артефакт '{art.id}' не найден: {full}. "
                    "Перед result() надо записать файл в output_dir."
                )

        self._emit(ResultEvent(artifacts=normalized))
        self._finished = True

    def failed(self, msg: str, details: str | None = None) -> None:
        """Финальное событие неуспеха."""
        if self._finished:
            raise RuntimeError(_FINISHED_MSG)
        self._emit(FailedEvent(msg=msg, details=details))
        self._finished = True

    def _normalize_artifact(self, a: dict[str, str]) -> Artifact:
        if not isinstance(a, dict):
            raise TypeError(
                "artifacts должны быть list[dict] вида [{'id': ..., 'path': ...}], "
                f"получено: {a!r}"
            )
        return Artifact(**a)

    # --- Внутреннее ---

    def _emit(self, event: BaseModel) -> None:
        try:
            line = event.model_dump_json(exclude_none=True)
        except (TypeError, ValueError, ValidationError, PydanticSerializationError) as e:
            raise TypeError(
                f"Поле события {type(event).__name__} не JSON-сериализуемо: {e}. "
                "В data/summary можно класть только числа, строки, bool, None, "
                "списки и словари из этих типов. datetime — Pydantic сам сериализует."
            ) from None
        self._stdout.write(line + "\n")
        self._stdout.flush()
