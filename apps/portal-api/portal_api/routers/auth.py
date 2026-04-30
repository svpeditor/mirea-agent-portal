# ruff: noqa: B008
"""Auth endpoints: register / login / refresh / logout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import get_settings
from portal_api.deps import get_db
from portal_api.schemas.auth import AuthResponse, RegisterIn
from portal_api.schemas.user import UserOut
from portal_api.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_ttl_seconds,
        path="/api",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.jwt_refresh_ttl_seconds,
        path="/api/auth",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie("access_token", path="/api", domain=settings.cookie_domain)
    response.delete_cookie("refresh_token", path="/api/auth", domain=settings.cookie_domain)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
)
async def register(
    payload: RegisterIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    user, access, refresh = await auth_service.register(
        db,
        payload,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access, refresh)
    return AuthResponse(user=UserOut.model_validate(user))
