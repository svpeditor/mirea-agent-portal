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
