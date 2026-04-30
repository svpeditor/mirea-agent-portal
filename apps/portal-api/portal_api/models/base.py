"""Общий базовый класс для всех ORM-моделей."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех моделей. Всегда импортируй модели через portal_api.models."""
