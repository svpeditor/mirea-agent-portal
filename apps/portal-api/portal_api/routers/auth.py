# ruff: noqa: B008
"""Auth endpoints: register / login / refresh / logout."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import get_settings
from portal_api.deps import get_db
from portal_api.schemas.auth import AuthResponse, LoginIn, RegisterIn
from portal_api.schemas.user import UserOut
from portal_api.services import auth_service
from portal_api.services.invite_service import find_active_invite_by_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_ttl_seconds,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
    )
    # Дубль для WebSocket: cross-port handshake не получает httpOnly access_token
    # из Set-Cookie. Этот cookie не httpOnly — frontend читает document.cookie
    # и подставляет в ws://...?token=. Содержит тот же JWT, но без httpOnly.
    response.set_cookie(
        key="ws_token",
        value=access_token,
        max_age=settings.jwt_access_ttl_seconds,
        path="/",
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.jwt_refresh_ttl_seconds,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        "access_token",
        path="/",
        domain=settings.cookie_domain,
        samesite="lax",
        secure=settings.cookie_secure,
        httponly=True,
    )
    response.delete_cookie(
        "ws_token",
        path="/",
        domain=settings.cookie_domain,
        samesite="lax",
        secure=settings.cookie_secure,
        httponly=False,
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        domain=settings.cookie_domain,
        samesite="lax",
        secure=settings.cookie_secure,
        httponly=True,
    )


@router.get("/invite-info")
async def invite_info(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Возвращает email из invite token, если он валиден.

    Используется фронтом на странице /register для предзаполнения email.
    Кидает InviteInvalid (→ 4xx с error.code = "invite_invalid") при истёкшем/использованном/неизвестном токене.
    """
    invite = await find_active_invite_by_token(db, token)
    return {"email": invite.email}


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


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    user, access, refresh = await auth_service.login(
        db,
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access, refresh)
    return AuthResponse(user=UserOut.model_validate(user))


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await auth_service.logout(db, refresh_token)
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    user, access, new_refresh = await auth_service.refresh(
        db,
        refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access, new_refresh)
    return AuthResponse(user=UserOut.model_validate(user))
