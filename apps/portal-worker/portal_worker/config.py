"""Настройки worker через pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn, RedisDsn, field_validator
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
    portal_sdk_path: Path = Path("/portal-sdk")

    # Таймауты сборки
    build_timeout_seconds: int = 600
    build_clone_timeout_seconds: int = 60

    # Лимиты размеров при сборке
    build_max_repo_size_bytes: int = 50 * 1024 * 1024
    build_max_image_size_bytes: int = 2 * 1024**3
    build_memory_limit_bytes: int = 2 * 1024**3

    # Whitelist base-images для Dockerfile-gen
    allowed_base_images: list[str] = [
        "python:3.11-slim",
        "python:3.12-slim",
        "python:3.13-slim",
    ]

    # Лимиты и хранилище для jobs (1.2.3)
    max_job_input_bytes: int = 100 * 1024 * 1024
    max_job_output_bytes: int = 1024**3
    job_timeout_seconds: int = 1800
    file_store_local_root: Path = Path("/var/portal-files")

    # LLM proxy (1.2.4)
    llm_proxy_base_url: str = "http://portal-api:8000/llm/v1"
    llm_agents_network_name: str = "portal-agents-net"
    llm_allowed_models: list[str] | str = []  # noqa: RUF002

    @field_validator("llm_allowed_models", mode="before")
    @classmethod
    def _split_csv_models(cls, v: object) -> object:
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        return v

    # Логирование
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # populated from env
