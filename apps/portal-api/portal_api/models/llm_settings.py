"""ORM-модель: singleton-настройки LLM, редактируемые из admin-UI.

Секреты тут хранятся, но НИКОГДА не сериализуются клиенту целиком —
admin-эндпоинт маскирует, логи не пишут значения.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from portal_api.models.base import Base


class LlmSettings(Base):
    __tablename__ = "llm_settings"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    openrouter_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_mode: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'openrouter'"),
    )
    openai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    xai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    anthropic_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    deepseek_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_models: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
