"""Настройки приложения через pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic import EmailStr, PostgresDsn, SecretStr
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
