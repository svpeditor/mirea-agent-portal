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


class TabSlugTakenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="TAB_SLUG_TAKEN",
            message="Slug этой вкладки уже занят.",
            status_code=409,
        )


class TabNotEmptyError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="TAB_NOT_EMPTY",
            message="Нельзя удалить вкладку, в которой есть агенты.",
            status_code=409,
        )


class TabIsSystemError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="TAB_IS_SYSTEM",
            message="Системную вкладку нельзя удалять или менять её slug.",
            status_code=403,
        )


class TabNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="TAB_NOT_FOUND",
            message="Вкладка не найдена.",
            status_code=404,
        )


class InvalidGitUrlError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_GIT_URL",
            message="Git URL должен быть https-ссылкой на доступный репозиторий.",
            status_code=400,
        )


class InvalidGitRefError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_GIT_REF",
            message="Не удалось зарезолвить git-ref в SHA.",
            status_code=400,
        )


class AgentSlugTakenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="AGENT_SLUG_TAKEN",
            message="Агент с таким slug уже существует.",
            status_code=409,
        )


class AgentNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="AGENT_NOT_FOUND",
            message="Агент не найден.",
            status_code=404,
        )


class ManifestInvalidError(AppError):
    def __init__(self, message: str = "manifest.yaml не прошёл валидацию.") -> None:
        super().__init__(
            code="MANIFEST_INVALID",
            message=message,
            status_code=400,
        )


class ManifestNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="MANIFEST_NOT_FOUND",
            message="manifest.yaml не найден в репозитории по указанному ref.",
            status_code=400,
        )


class BaseImageNotAllowedError(AppError):
    def __init__(self, base_image: str) -> None:
        super().__init__(
            code="BASE_IMAGE_NOT_ALLOWED",
            message=f"base_image '{base_image}' не входит в whitelist портала.",
            status_code=400,
        )


class AgentHasVersionsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="AGENT_HAS_VERSIONS",
            message="Сначала удалите все версии агента.",
            status_code=409,
        )


class NoReadyVersionError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="NO_READY_VERSION",
            message=(
                "Включить агента можно только когда у него есть готовая (ready) "
                "версия и она помечена как current."
            ),
            status_code=409,
        )


class VersionNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="VERSION_NOT_FOUND",
            message="Версия агента не найдена.",
            status_code=404,
        )


class VersionAlreadyExistsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="VERSION_ALREADY_EXISTS",
            message="Версия с таким git_sha уже существует у этого агента.",
            status_code=409,
        )


class VersionNotReadyError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="VERSION_NOT_READY",
            message="Только версии в статусе ready могут быть current.",
            status_code=409,
        )


class VersionIsCurrentError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="VERSION_IS_CURRENT",
            message="Эта версия — текущая (current). Сначала переключите current на другую.",
            status_code=409,
        )


class RetryNotFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="RETRY_NOT_FAILED",
            message="Retry применим только к версиям в статусе failed.",
            status_code=400,
        )


class AgentNotReadyError(AppError):
    """current_version агента не в status='ready'."""

    def __init__(self) -> None:
        super().__init__(
            code="agent_not_ready",
            message="Текущая версия агента не готова (status != 'ready').",
            status_code=409,
        )


class JobNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="job_not_found",
            message="Job не найден.",
            status_code=404,
        )


class JobAlreadyFinishedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="job_already_finished",
            message="Job уже завершён.",
            status_code=409,
        )


class InputsTooLargeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="inputs_too_large",
            message="Размер входных данных превышает допустимый лимит.",
            status_code=413,
        )


class InputFilenameInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="input_filename_invalid",
            message="Недопустимое имя файла.",
            status_code=400,
        )


class ParamsInvalidJsonError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="params_invalid_json",
            message="Параметры не являются корректным JSON.",
            status_code=400,
        )


class QuotaExhaustedError(AppError):
    """Месячная квота юзера исчерпана."""

    def __init__(self, message: str = "Месячная квота исчерпана.") -> None:
        super().__init__(code="quota_exhausted", message=message, status_code=402)


class PerJobCapExceededError(AppError):
    """На текущем job уже потрачено сверх per_job_cap_usd."""

    def __init__(self, message: str = "Превышен лимит стоимости на один job.") -> None:
        super().__init__(code="per_job_cap_exceeded", message=message, status_code=402)


class ModelNotInWhitelistError(AppError):
    """Модель из request.body не разрешена manifest агента."""

    def __init__(self, message: str = "Модель не разрешена для этого агента.") -> None:
        super().__init__(code="model_not_in_whitelist", message=message, status_code=403)


class InvalidEphemeralTokenError(AppError):
    """Bearer token не существует / истёк / отозван."""

    def __init__(self, message: str = "Ephemeral-токен недействителен или истёк.") -> None:
        super().__init__(code="invalid_ephemeral_token", message=message, status_code=401)


class OpenRouterUpstreamError(AppError):
    """OpenRouter вернул 5xx."""

    def __init__(self, message: str = "Ошибка upstream OpenRouter.") -> None:
        super().__init__(code="openrouter_upstream_error", message=message, status_code=502)


class OpenRouterTimeoutError(AppError):
    """OpenRouter не ответил за timeout."""

    def __init__(self, message: str = "OpenRouter не ответил за отведённое время.") -> None:
        super().__init__(code="openrouter_timeout", message=message, status_code=504)
