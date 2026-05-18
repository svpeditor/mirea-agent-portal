"""Admin LLM-настройки: GET (маскированно) + PUT. Секреты НИКОГДА не
возвращаются целиком и не пишутся в аудит/логи (только имена изменённых
полей)."""
# ruff: noqa: B008
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.deps import get_db, require_admin
from portal_api.models import User
from portal_api.schemas.llm_settings import LlmSettingsUpdateIn
from portal_api.services import audit_service, llm_settings_service
from portal_api.services.audit_service import A as Action

router = APIRouter(prefix="/admin", tags=["admin", "llm-settings"])


@router.get("/llm-settings")
async def get_llm_settings(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    return await llm_settings_service.get_masked(db, settings)


@router.put("/llm-settings")
async def put_llm_settings(
    payload: LlmSettingsUpdateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    # только реально присланные поля (отсутствие = не менять)
    patch = payload.model_dump(include=payload.model_fields_set)
    changed = await llm_settings_service.update(
        db, actor_user_id=admin.id, patch=patch,
    )
    ip, ua = audit_service.request_meta(request)
    await audit_service.log_action(
        db,
        actor_user_id=admin.id,
        action=Action.LLM_SETTINGS_UPDATE,
        resource_type="llm_settings",
        resource_id="1",
        payload={"changed": changed},  # ТОЛЬКО имена полей, без значений
        ip=ip,
        user_agent=ua,
    )
    await db.commit()
    return await llm_settings_service.get_masked(db, settings)
