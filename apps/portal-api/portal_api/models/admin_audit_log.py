"""SQLAlchemy ORM для admin_audit_log."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from portal_api.models.base import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    action: Mapped[str] = mapped_column(Text(), nullable=False)
    resource_type: Mapped[str] = mapped_column(Text(), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict, server_default="{}",
    )
    ip: Mapped[str | None] = mapped_column(Text(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )
