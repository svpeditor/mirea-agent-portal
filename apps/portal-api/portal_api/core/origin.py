# ruff: noqa: RUF001, RUF002
"""Middleware проверки Origin для cookie-based auth."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from portal_api.config import get_settings

_UNSAFE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Проверяет Origin/Referer на не-GET запросах.

    Без проверки cookie-аутентификация уязвима к CSRF-подобным атакам со
    стороны других origin'ов (SameSite=Strict защищает большинство, но
    дополнительная проверка не повредит и ловит несовпадающие proxy).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in _UNSAFE_METHODS:
            settings = get_settings()
            origin = request.headers.get("origin") or request.headers.get("referer")
            allowed = set(settings.allowed_origins)
            if origin is None:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "ORIGIN_MISMATCH",
                            "message": "Origin header обязателен для не-GET запросов.",
                        }
                    },
                )
            ok = any(origin == a or origin.rstrip("/") == a.rstrip("/") for a in allowed)
            if not ok:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "ORIGIN_MISMATCH",
                            "message": "Запрос с недопустимого origin.",
                        }
                    },
                )
        return await call_next(request)
