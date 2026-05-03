"""Pytest конфигурация — реальный Postgres через testcontainers + fixtures."""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Сразу выставим ENV на всё session, чтобы Settings прошли валидацию
# Реальный DATABASE_URL подменим в фикстуре `_setup_database_url`
os.environ.setdefault("JWT_SECRET", "x" * 64)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://stub:stub@stub/stub")
# NB: не выставляем ENVIRONMENT=test через setdefault — это утекает в test_config
# через os.environ. Settings.environment уже defaults to "dev".
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-v1-test-stub")


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    """Один Postgres-контейнер на всю test-сессию."""
    with PostgresContainer(
        "postgres:16-alpine", username="test", password="test", dbname="test"
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    """Один Redis-контейнер на всю test-сессию (broker для RQ)."""
    with RedisContainer("redis:7-alpine") as r:
        yield r


@pytest.fixture
def redis_url(redis_container: RedisContainer) -> str:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture
def reset_redis(redis_container: RedisContainer) -> Iterator[None]:
    """Перед/после каждого теста, который трогает Redis, очищаем БД."""
    import redis as redis_lib

    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = redis_lib.Redis(host=host, port=int(port), db=0)
    client.flushdb()
    try:
        yield
    finally:
        client.flushdb()
        client.close()


@pytest.fixture(scope="session")
def _setup_database_url(postgres_container: PostgresContainer) -> Iterator[str]:
    """Подменяет DATABASE_URL в env на реальный контейнер."""
    raw_url = postgres_container.get_connection_url()
    # testcontainers возвращает psycopg2-вариант; нам нужен asyncpg
    url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    os.environ["DATABASE_URL"] = url
    os.environ["ALLOWED_ORIGINS"] = '["http://test"]'
    # Сбросить кеш Settings и engine
    from portal_api import config, db

    config.get_settings.cache_clear()
    db._engine = None
    db._sessionmaker = None
    yield url


def _make_alembic_config():  # type: ignore[no-untyped-def]
    """Сборка Alembic Config для тестов (использует уже подменённый DATABASE_URL)."""
    from alembic.config import Config

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option(
        "script_location", os.path.join(os.path.dirname(__file__), "..", "alembic")
    )
    return cfg


@pytest_asyncio.fixture(scope="session")
async def _migrated(_setup_database_url: str) -> AsyncIterator[None]:
    """Прогоняет alembic upgrade head на тестовом Postgres."""
    from alembic import command

    cfg = _make_alembic_config()
    # Run в синхронном режиме через alembic — оно само поднимает event loop
    await asyncio.to_thread(command.upgrade, cfg, "head")
    yield


@pytest.fixture
def alembic_config(_migrated: None):  # type: ignore[no-untyped-def]
    """Alembic Config для downgrade/upgrade в тестах миграций."""
    return _make_alembic_config()


@pytest_asyncio.fixture
async def db_engine(_migrated: None) -> AsyncIterator:  # type: ignore[type-arg]
    """Async engine, подключённый к мигрированной тестовой БД.

    Используется в тестах миграций, которые сами управляют транзакциями
    и DDL-проверками (через `inspect`).
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db(_migrated: None) -> AsyncIterator[AsyncSession]:
    """Свежая транзакция на каждый тест, откатывается после теста.

    Все тесты в этой сессии используют ОДНУ БД, изоляция через rollback.
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        trans = await conn.begin()
        session_local = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with session_local() as session:
            try:
                yield session
            finally:
                await session.close()
        await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """httpx-клиент к FastAPI с подменённым get_db."""
    # Снизим bcrypt cost для скорости тестов
    monkeypatch.setenv("BCRYPT_COST_TESTING", "4")

    from portal_api.deps import get_db
    from portal_api.main import app

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Origin": "http://test"},
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):  # type: ignore[no-untyped-def]
    """Готовый админ. Пароль 'test-pass'."""
    from tests.factories import UserFactory

    return await UserFactory.create(db, role="admin", password="test-pass")


@pytest_asyncio.fixture
async def regular_user(db: AsyncSession):  # type: ignore[no-untyped-def]
    """Готовый обычный юзер. Пароль 'test-pass'."""
    from tests.factories import UserFactory

    return await UserFactory.create(db, role="user", password="test-pass")


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, admin_user) -> AsyncClient:  # type: ignore[no-untyped-def]
    """httpx-клиент уже залогинен админом."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest_asyncio.fixture
async def user_client(client: AsyncClient, regular_user) -> AsyncClient:  # type: ignore[no-untyped-def]
    """httpx-клиент уже залогинен обычным юзером."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest_asyncio.fixture
async def normal_user(db: AsyncSession):  # type: ignore[no-untyped-def]
    """Обычный юзер с UserQuota (аналог invite-flow register). Пароль 'test-pass'."""
    from datetime import UTC, datetime
    from decimal import Decimal

    from portal_api.models import UserQuota
    from portal_api.services.llm_quota import _floor_to_month_start_msk_utc
    from tests.factories import UserFactory

    user = await UserFactory.create(db, role="user", password="test-pass")
    quota = UserQuota(
        user_id=user.id,
        monthly_limit_usd=Decimal("5.0000"),
        period_used_usd=Decimal("0.0000"),
        per_job_cap_usd=Decimal("0.5000"),
        period_starts_at=_floor_to_month_start_msk_utc(datetime.now(UTC)),
    )
    db.add(quota)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def normal_user_token(client: AsyncClient, normal_user) -> str:  # type: ignore[no-untyped-def]
    """access_token для normal_user (JWT строка для Cookie-заголовка)."""
    from portal_api.core.security import create_access_token

    # Генерируем токен напрямую — надёжнее чем парсить cookie из httpx-ответа
    return create_access_token(user_id=str(normal_user.id), role=normal_user.role)


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user) -> str:  # type: ignore[no-untyped-def]
    """access_token для admin_user (JWT строка для Cookie-заголовка)."""
    from portal_api.core.security import create_access_token

    return create_access_token(user_id=str(admin_user.id), role=admin_user.role)


@pytest.fixture
def db_sessionmaker(_migrated: None) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker, подключённый к тестовому Postgres.

    Используется в тестах, которые сами создают app с dependency_overrides
    (напр. test_llm_auth.py). Каждый вызов sessionmaker() открывает новую
    сессию без автоматического rollback — изоляция обеспечивается тестовым
    порядком.
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest.fixture(autouse=True)
def _reset_engine() -> Iterator[None]:
    """Сбрасываем глобальный engine между тестами, чтобы не текло между rollbacks."""
    yield
