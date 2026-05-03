"""Парсер JSONL-потока stdout агента: строка = JSON-event."""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import Any


def parse_jsonl_stream(
    stream: Iterable[bytes], *, flush_on_eof: bool = True,
) -> Iterator[dict[str, Any]]:
    """Стримит чанки байт, ёмитит JSON dict на каждой полной строке.

    Невалидный JSON → ёмитим event {"type":"error","msg":"invalid_json: ..."}.
    Пустые строки игнорируем.
    Если flush_on_eof=True и в буфере осталась незакрытая строка — ёмитим её.
    """
    buf = b""
    for chunk in stream:
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            event = _try_parse(line)
            if event is not None:
                yield event
    if flush_on_eof and buf.strip():
        event = _try_parse(buf)
        if event is not None:
            yield event


def _try_parse(line: bytes) -> dict[str, Any] | None:
    s = line.strip()
    if not s:
        return None
    try:
        obj = json.loads(s.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        return {"type": "error", "msg": f"invalid_json: {exc.msg[:80]}"}
    if not isinstance(obj, dict):
        return {"type": "error", "msg": "invalid_json: not an object"}
    return obj
