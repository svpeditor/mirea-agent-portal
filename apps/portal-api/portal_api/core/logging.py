"""structlog config + processor для фильтрации чувствительных полей."""
from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

_SENSITIVE_KEYS = frozenset({
    "password",
    "current_password",
    "new_password",
    "password_hash",
    "token",
    "refresh_token",
    "access_token",
})


def _redact_sensitive(
    _logger: Any,
    _name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Заменяет значения чувствительных ключей на '***'."""
    for k in list(event_dict.keys()):
        if k.lower() in _SENSITIVE_KEYS:
            event_dict[k] = "***"
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _redact_sensitive,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
    )
