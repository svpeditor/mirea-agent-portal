"""Тест init_sentry — без DSN noop, с DSN не падает."""
from __future__ import annotations

from copy import copy

import pytest

from portal_api.config import Settings, get_settings
from portal_api.core.sentry import init_sentry


def _settings_with(**overrides) -> Settings:  # type: ignore[no-untyped-def]
    base = get_settings()
    s = copy(base)
    for k, v in overrides.items():
        object.__setattr__(s, k, v)
    return s


def test_init_sentry_noop_without_dsn() -> None:
    s = _settings_with(sentry_dsn=None)
    init_sentry(s)  # не должно бросить


@pytest.mark.parametrize("dsn", ["https://public@sentry.example.com/1"])
def test_init_sentry_with_dsn_does_not_raise(dsn: str) -> None:
    """С валидным форматом DSN init_sentry успешно настраивает Sentry."""
    s = _settings_with(
        sentry_dsn=dsn,
        sentry_traces_sample_rate=0.1,
        sentry_release="test-0.1.0",
        environment="test",
    )
    init_sentry(s)  # успешно завершается, не пытается отправить события сейчас
