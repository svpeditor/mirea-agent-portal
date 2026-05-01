"""Pytest config -- Postgres + Redis via testcontainers."""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Stub so Settings validation passes before containers are ready
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://stub:stub@stub/stub")


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer]:
    """Single Postgres 16 container for the whole test session."""
    with PostgresContainer(
        "postgres:16-alpine", username="test", password="test", dbname="test"
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    """Single Redis container for the whole test session."""
    with RedisContainer("redis:7-alpine") as r:
        yield r


@pytest.fixture(scope="session")
def settings_env(
    pg_container: PostgresContainer,
    redis_container: RedisContainer,
) -> Iterator[None]:
    """Patch DATABASE_URL and REDIS_URL env vars for the entire session."""
    raw_url = pg_container.get_connection_url()
    # testcontainers returns psycopg2 URL; normalise just in case
    db_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    os.environ["DATABASE_URL"] = db_url
    os.environ["REDIS_URL"] = redis_url

    # Clear lru_cache so Settings picks up the new env vars
    from portal_worker import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture(scope="session")
def db_with_schema(settings_env: None, pg_container: PostgresContainer) -> Iterator[None]:
    """Create minimal DB schema for tests (no alembic dependency)."""
    raw_url = pg_container.get_connection_url()
    db_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                monthly_budget_usd NUMERIC(10,2) NOT NULL DEFAULT 5.00,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tabs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                icon TEXT,
                order_idx INTEGER NOT NULL DEFAULT 0,
                is_system BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                icon TEXT,
                short_description TEXT NOT NULL,
                tab_id UUID NOT NULL REFERENCES tabs(id) ON DELETE RESTRICT,
                current_version_id UUID,
                enabled BOOLEAN NOT NULL DEFAULT false,
                git_url TEXT NOT NULL,
                created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
                git_sha TEXT NOT NULL,
                git_ref TEXT NOT NULL,
                manifest_jsonb JSONB NOT NULL,
                manifest_version TEXT NOT NULL,
                docker_image_tag TEXT,
                status TEXT NOT NULL,
                build_log TEXT,
                build_started_at TIMESTAMPTZ,
                build_finished_at TIMESTAMPTZ,
                build_error TEXT,
                created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT agent_versions_status_check
                    CHECK (status IN ('pending_build','building','ready','failed')),
                CONSTRAINT agent_versions_agent_id_git_sha_key
                    UNIQUE (agent_id, git_sha)
            )
        """))
    engine.dispose()
    yield
