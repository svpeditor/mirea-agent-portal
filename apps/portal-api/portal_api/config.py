"""Настройки приложения через pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import EmailStr, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # БД
    database_url: PostgresDsn

    # JWT
    jwt_secret: SecretStr
    jwt_access_ttl_seconds: int = 86400  # 24ч
    jwt_refresh_ttl_seconds: int = 2592000  # 30 дней

    # Bootstrap первого админа
    initial_admin_email: EmailStr | None = None
    initial_admin_password: SecretStr | None = None

    # CORS / CSRF — список origin'ов, которым разрешён cookie-доступ
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Cookies
    cookie_secure: bool = False
    cookie_domain: str | None = None

    # Misc
    log_level: str = "INFO"
    environment: str = "dev"

    # Redis (RQ broker для билд-очереди)
    redis_url: RedisDsn = "redis://redis:6379/0"  # type: ignore[assignment]

    # Builder: разрешённые base-images для Dockerfile-gen
    allowed_base_images: list[str] = [
        "python:3.11-slim",
        "python:3.12-slim",
        "python:3.13-slim",
    ]

    # Лимиты и хранилище для jobs (1.2.3)
    max_job_input_bytes: int = 100 * 1024 * 1024
    max_job_output_bytes: int = 1024**3
    job_timeout_seconds: int = 1800
    file_store_backend: Literal["local"] = "local"
    file_store_local_root: Path = Path("/var/portal-files")


@lru_cache
def get_settings() -> Settings:
    return Settings()
