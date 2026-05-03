"""ORM-модели для 1.2.4 LLM-прокси: UserQuota, EphemeralToken, UsageLog."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portal_api.models.base import Base


class UserQuota(Base):
    __tablename__ = "user_quotas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    monthly_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=sa.text("5.0000"),
    )
    period_used_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=sa.text("0.0000"),
    )
    period_starts_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False,
    )
    per_job_cap_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=sa.text("0.5000"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="quota")  # noqa: F821


class EphemeralToken(Base):
    __tablename__ = "llm_ephemeral_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agent_versions.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True,
    )


class UsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False,
    )
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agent_versions.id"), nullable=False,
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    openrouter_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(),
    )
