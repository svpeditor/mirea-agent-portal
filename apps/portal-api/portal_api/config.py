"""Настройки приложения через pydantic-settings."""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import EmailStr, PostgresDsn, RedisDsn, SecretStr, field_validator
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

    # LLM proxy (1.2.4)
    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_allowed_models: list[str] | str = []  # noqa: RUF002
    llm_default_user_quota_usd: Decimal = Decimal("5.0000")
    llm_default_per_job_cap_usd: Decimal = Decimal("0.5000")
    llm_pricing_refresh_interval_seconds: int = 21600
    llm_request_timeout_seconds: int = 30
    llm_proxy_base_url: str = "http://portal-api:8000/llm/v1"

    @field_validator("llm_allowed_models", mode="before")
    @classmethod
    def _split_csv_models(cls, v: object) -> object:
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
