"""parse_jsonl_stream: построчный JSON-парсер с буферизацией."""  # noqa: RUF002
from __future__ import annotations

from portal_worker.runner.jsonl_parser import parse_jsonl_stream


def _stream(*chunks: bytes):
    yield from chunks


def test_parses_complete_lines() -> None:
    s = _stream(b'{"type":"started"}\n', b'{"type":"progress","value":0.5}\n')
    events = list(parse_jsonl_stream(s))
    assert events == [
        {"type": "started"},
        {"type": "progress", "value": 0.5},
    ]


def test_buffers_partial_line() -> None:
    s = _stream(b'{"type":"start', b'ed"}\n')
    events = list(parse_jsonl_stream(s))
    assert events == [{"type": "started"}]


def test_emits_error_on_invalid_json() -> None:
    s = _stream(b'NOT-JSON\n', b'{"type":"ok"}\n')
    events = list(parse_jsonl_stream(s))
    assert len(events) == 2
    assert events[0]["type"] == "error"
    assert "invalid_json" in events[0]["msg"]
    assert events[1] == {"type": "ok"}


def test_skips_empty_lines() -> None:
    s = _stream(b'\n\n{"type":"x"}\n\n')
    events = list(parse_jsonl_stream(s))
    assert events == [{"type": "x"}]


def test_handles_no_trailing_newline() -> None:
    """Финальная строка без \\n должна выйти если генератор кончился."""
    s = _stream(b'{"type":"a"}\n', b'{"type":"b"}')  # b без \n
    events = list(parse_jsonl_stream(s, flush_on_eof=True))
    assert events == [{"type": "a"}, {"type": "b"}]
