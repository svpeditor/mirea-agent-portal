"""DTO для admin audit log."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    payload: dict[str, Any]
    ip: str | None
    user_agent: str | None
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: Any) -> AuditLogOut:
        return cls(
            id=row.id,
            actor_user_id=row.actor_user_id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            payload=row.payload_jsonb or {},
            ip=row.ip,
            user_agent=row.user_agent,
            created_at=row.created_at,
        )
