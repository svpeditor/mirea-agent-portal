"""Per-request structured logging middleware."""
from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

_log = structlog.get_logger(__name__)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Логирует каждый запрос: request_id, method, path, status, duration_ms, user_id."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            _log.exception(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise
        duration_ms = int((time.perf_counter() - start) * 1000)
        # user_id from access cookie/jwt — keep simple: omit if not present
        _log.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=status,
            duration_ms=duration_ms,
        )
        response.headers["x-request-id"] = request_id
        return response
