"""NDJSON-события: агент пишет в stdout, портал читает."""
from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class _EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartedEvent(_EventBase):
    type: Literal["started"] = "started"
    ts: str  # ISO-8601


class ProgressEvent(_EventBase):
    type: Literal["progress"] = "progress"
    value: float = Field(ge=0.0, le=1.0)
    label: str | None = None


class LogEvent(_EventBase):
    type: Literal["log"] = "log"
    level: LogLevel = LogLevel.INFO
    msg: str


class ItemDoneEvent(_EventBase):
    type: Literal["item_done"] = "item_done"
    id: str
    summary: str | None = None
    data: dict[str, Any] | None = None


class ErrorEvent(_EventBase):
    type: Literal["error"] = "error"
    id: str | None = None
    msg: str
    retryable: bool = True


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    path: str  # относительно $OUTPUT_DIR


class ResultEvent(_EventBase):
    type: Literal["result"] = "result"
    artifacts: list[Artifact] = Field(default_factory=list)


class FailedEvent(_EventBase):
    type: Literal["failed"] = "failed"
    msg: str
    details: str | None = None


Event = Annotated[
    StartedEvent | ProgressEvent | LogEvent | ItemDoneEvent | ErrorEvent | ResultEvent | FailedEvent,
    Field(discriminator="type"),
]


_event_adapter: TypeAdapter[Event] = TypeAdapter(Event)


def parse_event_line(line: str) -> Event:
    """Распарсить одну NDJSON-строку в типизированное событие."""
    data = json.loads(line)
    return _event_adapter.validate_python(data)
