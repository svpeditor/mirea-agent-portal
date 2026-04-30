"""Тесты NDJSON-событий контракта."""
import json

import pytest
from pydantic import ValidationError

from portal_sdk.events import Event as _Event  # smoke: проверяем что публичный реэкспорт работает
from portal_sdk.events import (
    LogLevel,
    parse_event_line,
)

# smoke: убеждаемся что Event публично доступен (не только через Annotated)
assert _Event is not None


def test_started_event_serializes() -> None:
    line = '{"type":"started","ts":"2026-04-30T15:01:00Z"}'
    ev = parse_event_line(line)
    assert ev.type == "started"
    assert ev.ts == "2026-04-30T15:01:00Z"


def test_progress_event() -> None:
    line = '{"type":"progress","value":0.5,"label":"Half"}'
    ev = parse_event_line(line)
    assert ev.type == "progress"
    assert ev.value == 0.5
    assert ev.label == "Half"


def test_progress_value_range_validated() -> None:
    with pytest.raises(ValidationError):
        parse_event_line('{"type":"progress","value":1.5}')


def test_log_event_with_level() -> None:
    line = '{"type":"log","level":"warn","msg":"Watch out"}'
    ev = parse_event_line(line)
    assert ev.type == "log"
    assert ev.level == LogLevel.WARN


def test_item_done_event() -> None:
    line = '{"type":"item_done","id":"01","summary":"OK","data":{"score":7}}'
    ev = parse_event_line(line)
    assert ev.type == "item_done"
    assert ev.id == "01"
    assert ev.data == {"score": 7}


def test_error_event_default_retryable() -> None:
    line = '{"type":"error","msg":"oops"}'
    ev = parse_event_line(line)
    assert ev.type == "error"
    assert ev.retryable is True


def test_result_event_with_artifacts() -> None:
    line = '{"type":"result","artifacts":[{"id":"r","path":"out.docx"}]}'
    ev = parse_event_line(line)
    assert ev.type == "result"
    assert ev.artifacts[0].id == "r"
    assert ev.artifacts[0].path == "out.docx"


def test_failed_event() -> None:
    line = '{"type":"failed","msg":"crashed","details":"traceback..."}'
    ev = parse_event_line(line)
    assert ev.type == "failed"


def test_unknown_type_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_event_line('{"type":"weird"}')


def test_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_event_line("not json at all")


def test_event_to_ndjson_round_trip() -> None:
    """Событие сериализуется в одну строку без переносов."""
    line = '{"type":"progress","value":0.3,"label":"a"}'
    ev = parse_event_line(line)
    out = ev.model_dump_json(exclude_none=True)
    assert "\n" not in out
    assert json.loads(out)["type"] == "progress"
