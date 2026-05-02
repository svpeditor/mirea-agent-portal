"""Settings читается из ENV и валидирует поля."""
import pytest


def test_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("JWT_SECRET", "x" * 64)

    from portal_api.config import Settings

    settings = Settings()

    assert str(settings.database_url) == "postgresql+asyncpg://u:p@h:5432/d"
    assert settings.jwt_secret.get_secret_value() == "x" * 64
    assert settings.jwt_access_ttl_seconds == 86400
    assert settings.jwt_refresh_ttl_seconds == 2592000
    assert settings.cookie_secure is False
    assert settings.environment == "dev"


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET", "x" * 64)

    from portal_api.config import Settings

    with pytest.raises(ValueError, match="database_url"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_allowed_origins_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("JWT_SECRET", "x" * 64)
    monkeypatch.setenv("ALLOWED_ORIGINS", '["http://localhost:3000","http://x.test"]')

    from portal_api.config import Settings

    settings = Settings()
    assert settings.allowed_origins == ["http://localhost:3000", "http://x.test"]


def test_settings_default_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)

    from portal_api.config import Settings

    s = Settings()  # type: ignore[call-arg]
    assert str(s.redis_url) == "redis://redis:6379/0"


def test_settings_allowed_base_images_default() -> None:
    from portal_api.config import Settings

    assert Settings.model_fields["allowed_base_images"].default == [
        "python:3.11-slim",
        "python:3.12-slim",
        "python:3.13-slim",
    ]


def test_settings_redis_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("REDIS_URL", "redis://other:6380/3")

    from portal_api.config import Settings

    s = Settings()  # type: ignore[call-arg]
    assert str(s.redis_url) == "redis://other:6380/3"


def test_settings_loads_job_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from portal_api.config import Settings

    s = Settings(
        database_url="postgresql+asyncpg://u:p@h/db",
        redis_url="redis://r:6379/0",
        jwt_secret="x" * 32,
        initial_admin_email="a@example.com",
        initial_admin_password="passwordpassword",
    )
    assert s.max_job_input_bytes == 100 * 1024 * 1024
    assert s.max_job_output_bytes == 1024**3
    assert s.job_timeout_seconds == 1800
    assert s.file_store_backend == "local"
    assert str(s.file_store_local_root) == "/var/portal-files"
