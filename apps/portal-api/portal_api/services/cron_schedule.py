"""Утилиты для расчёта next_run_at."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta


def next_run_after(now: datetime, schedule: str) -> datetime:
    """Возвращает следующий момент запуска относительно `now` по пресету.

    Пресеты:
    - hourly:  +1 час
    - daily:   +1 день
    - weekly:  +7 дней
    - monthly: +1 календарный месяц
    """
    if schedule == "hourly":
        return now + timedelta(hours=1)
    if schedule == "daily":
        return now + timedelta(days=1)
    if schedule == "weekly":
        return now + timedelta(days=7)
    if schedule == "monthly":
        return now + relativedelta(months=1)
    raise ValueError(f"unknown schedule preset: {schedule!r}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
