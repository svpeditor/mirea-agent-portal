"""ORM-модель User."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portal_api.models.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="users_role_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, server_default="user")
    monthly_budget_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("5.00")
    )
    avatar_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quota: Mapped["UserQuota | None"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan",
    )

    @property
    def has_avatar(self) -> bool:
        return self.avatar_storage_key is not None

    @property
    def avatar_version(self) -> str | None:
        """Короткий ID для cache-busting в URL аватара. None если аватара нет."""
        if not self.avatar_storage_key:
            return None
        # последние 8 hex-символов uuid из ключа avatars/<uid>/<uuid>
        return self.avatar_storage_key.rsplit("/", 1)[-1][:8]
