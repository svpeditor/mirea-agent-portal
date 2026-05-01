# ruff: noqa: N818, RUF001
"""AppError + коды ошибок согласно Спеку 1.2.1, раздел 8."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    """Базовое исключение для ожидаемых ошибок API."""

    code: str
    message: str
    status_code: int = 400
    details: list[dict[str, Any]] | None = None

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}: {self.message}"


# Готовые ошибки
class InviteInvalid(AppError):
    def __init__(self, message: str = "Приглашение недействительно или просрочено.") -> None:
        super().__init__(code="INVITE_INVALID", message=message, status_code=400)


class InvalidCredentials(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Неверный email или пароль.",
            status_code=401,
        )


class NotAuthenticated(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="NOT_AUTHENTICATED",
            message="Требуется авторизация.",
            status_code=401,
        )


class RefreshInvalid(AppError):
    def __init__(self, message: str = "Refresh-токен недействителен.") -> None:
        super().__init__(code="REFRESH_INVALID", message=message, status_code=401)


class RefreshReuseDetected(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="REFRESH_REUSE_DETECTED",
            message="Обнаружен повторный приём отозванного refresh — все сессии завершены.",
            status_code=401,
        )


class Forbidden(AppError):
    def __init__(self, message: str = "Недостаточно прав.") -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class OriginMismatch(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="ORIGIN_MISMATCH",
            message="Запрос с недопустимого origin.",
            status_code=403,
        )


class UserNotFound(AppError):
    def __init__(self) -> None:
        super().__init__(code="USER_NOT_FOUND", message="Пользователь не найден.", status_code=404)


class EmailAlreadyExists(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="EMAIL_ALREADY_EXISTS",
            message="Этот email уже зарегистрирован.",
            status_code=409,
        )


class EmailAlreadyRegistered(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="EMAIL_ALREADY_REGISTERED",
            message="Этот email уже зарегистрирован — приглашение не нужно.",
            status_code=409,
        )


class InviteAlreadyPending(AppError):
    def __init__(self, existing_id: str) -> None:
        super().__init__(
            code="INVITE_ALREADY_PENDING",
            message="На этот email уже выдано живое приглашение.",
            status_code=409,
            details=[{"existing_invite_id": existing_id}],
        )
