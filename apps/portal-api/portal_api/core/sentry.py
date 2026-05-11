"""Sentry-инициализация. Без `SENTRY_DSN` — no-op.

Использует sentry-sdk[fastapi] для авто-инструментации FastAPI/Starlette
и SQLAlchemy. PII выключен по умолчанию (request body / cookies в события
не попадают). Release/environment подставляются из Settings, если заданы.
"""
from __future__ import annotations

import logging

from portal_api.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    """Инициализировать Sentry если задан SENTRY_DSN. Иначе — noop."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("sentry_sdk не установлен — пропустил Sentry init")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.sentry_release,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
    )
    logger.info("Sentry инициализирован: env=%s release=%s",
                settings.environment, settings.sentry_release)
