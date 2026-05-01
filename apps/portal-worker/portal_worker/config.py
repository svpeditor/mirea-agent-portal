"""Настройки worker через pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # БД (sync, psycopg2)
    database_url: PostgresDsn

    # Redis broker для RQ
    redis_url: RedisDsn = "redis://redis:6379/0"  # type: ignore[assignment]

    # Путь к portal-sdk (опционально, для контейнера)
    portal_sdk_path: str = "/portal-sdk-src"

    # Таймауты сборки
    build_timeout_seconds: int = 600
    build_clone_timeout_seconds: int = 120

    # Whitelist base-images для Dockerfile-gen
    allowed_base_images: list[str] = [
        "python:3.11-slim",
        "python:3.12-slim",
        "python:3.13-slim",
    ]

    # Логирование
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # populated from env
