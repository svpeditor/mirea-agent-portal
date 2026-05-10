"""Sentry-инициализация для portal-worker."""
# ruff: noqa: RUF002
from __future__ import annotations

import logging

from portal_worker.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    """Инициализировать Sentry если задан SENTRY_DSN."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        logger.warning("sentry_sdk не установлен — пропустил Sentry init")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.sentry_release,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        integrations=[SqlalchemyIntegration()],
    )
    logger.info("Sentry инициализирован: env=%s release=%s",
                settings.environment, settings.sentry_release)
