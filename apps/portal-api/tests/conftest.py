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

# Сразу выставим ENV на всё session, чтобы Settings прошли валидацию
# Реальный DATABASE_URL подменим в фикстуре `_setup_database_url`
os.environ.setdefault("JWT_SECRET", "x" * 64)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://stub:stub@stub/stub")
# NB: не выставляем ENVIRONMENT=test через setdefault — это утекает в test_config
# через os.environ. Settings.environment уже defaults to "dev".
os.environ.setdefault("COOKIE_SECURE", "false")


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
def _setup_database_url(postgres_container: PostgresContainer) -> Iterator[str]:
    """Подменяет DATABASE_URL в env на реальный контейнер."""
    raw_url = postgres_container.get_connection_url()
    # testcontainers возвращает psycopg2-вариант; нам нужен asyncpg
    url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    os.environ["DATABASE_URL"] = url
    # Сбросить кеш Settings и engine
    from portal_api import config, db

    config.get_settings.cache_clear()
    db._engine = None
    db._sessionmaker = None
    yield url


@pytest_asyncio.fixture(scope="session")
async def _migrated(_setup_database_url: str) -> AsyncIterator[None]:
    """Прогоняет alembic upgrade head на тестовом Postgres."""
    from alembic.config import Config

    from alembic import command

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option(
        "script_location", os.path.join(os.path.dirname(__file__), "..", "alembic")
    )
    # Run в синхронном режиме через alembic — оно само поднимает event loop
    await asyncio.to_thread(command.upgrade, cfg, "head")
    yield


@pytest_asyncio.fixture
async def db(_migrated: None) -> AsyncIterator[AsyncSession]:
    """Свежая транзакция на каждый тест, откатывается после теста.

    Все тесты в этой сессии используют ОДНУ БД, изоляция через rollback.
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        trans = await conn.begin()
        session_local = async_sessionmaker(
            bind=conn, expire_on_commit=False, class_=AsyncSession
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


@pytest.fixture(autouse=True)
def _reset_engine() -> Iterator[None]:
    """Сбрасываем глобальный engine между тестами, чтобы не текло между rollbacks."""
    yield
