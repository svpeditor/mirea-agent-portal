"""Сервис аудита админских действий.

Любое мутирующее admin-действие должно записать строку в admin_audit_log.
Сервис отдаёт async-функцию `log_action(...)` — вызывается из роутеров
после успешного применения операции (если упало — нечего записывать).

Чтение через GET /api/admin/audit (см. routers/admin_audit.py): cursor
pagination, фильтры по action/resource_type/actor.
"""
# ruff: noqa: RUF002, S105
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import AdminAuditLog


async def log_action(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminAuditLog:
    """Записать строку в admin_audit_log.

    Не commit'ит — это делает caller. Так audit-запись попадает в ту же
    транзакцию, что и сама операция (либо обе закоммитятся, либо обе
    откатятся).
    """
    entry = AdminAuditLog(
        id=uuid.uuid4(),
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_jsonb=payload or {},
        ip=ip,
        user_agent=user_agent,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_audit(
    session: AsyncSession,
    *,
    limit: int = 50,
    before: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
) -> list[AdminAuditLog]:
    """Cursor pagination — (created_at DESC, id DESC). before=id предыдущей страницы."""
    stmt = select(AdminAuditLog)
    if actor_user_id is not None:
        stmt = stmt.where(AdminAuditLog.actor_user_id == actor_user_id)
    if action is not None:
        stmt = stmt.where(AdminAuditLog.action == action)
    if resource_type is not None:
        stmt = stmt.where(AdminAuditLog.resource_type == resource_type)
    if before is not None:
        before_row = (
            await session.execute(select(AdminAuditLog).where(AdminAuditLog.id == before))
        ).scalar_one_or_none()
        if before_row is not None:
            stmt = stmt.where(
                or_(
                    AdminAuditLog.created_at < before_row.created_at,
                    and_(
                        AdminAuditLog.created_at == before_row.created_at,
                        AdminAuditLog.id < before_row.id,
                    ),
                )
            )
    stmt = stmt.order_by(
        AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc()
    ).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


def request_meta(request: Any) -> tuple[str | None, str | None]:
    """(ip, user_agent) — для удобного inject из роутера."""
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return ip, user_agent


async def cleanup_older_than(session: AsyncSession, *, days: int) -> int:
    """Удалить audit-записи старше N дней. Возвращает количество удалённых."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete

    if days < 1:
        raise ValueError("days must be >= 1")
    cutoff = datetime.now(UTC) - timedelta(days=days)
    # COUNT перед DELETE для возврата
    result = await session.execute(
        select(AdminAuditLog.id).where(AdminAuditLog.created_at < cutoff),
    )
    ids = [row[0] for row in result.all()]
    if not ids:
        return 0
    await session.execute(
        delete(AdminAuditLog).where(AdminAuditLog.id.in_(ids)),
    )
    await session.flush()
    return len(ids)


# Стандартные actions для consistency между роутерами.
class A:
    INVITE_CREATE = "invite.create"
    INVITE_REVOKE = "invite.revoke"
    USER_RESET_PASSWORD = "user.reset_password"
    USER_UPDATE_QUOTA = "user.update_quota"
    USER_RESET_QUOTA = "user.reset_quota"
    USER_DELETE = "user.delete"
    AGENT_CREATE = "agent.create"
    AGENT_UPDATE = "agent.update"
    AGENT_DELETE = "agent.delete"
    AGENT_VERSION_CREATE = "agent_version.create"
    AGENT_VERSION_SET_CURRENT = "agent_version.set_current"
    AGENT_VERSION_DELETE = "agent_version.delete"
    TAB_CREATE = "tab.create"
    TAB_UPDATE = "tab.update"
    TAB_DELETE = "tab.delete"
