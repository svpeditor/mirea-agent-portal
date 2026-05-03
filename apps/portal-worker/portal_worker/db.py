"""Sync SQLAlchemy engine and session factory for the worker.

Uses psycopg2-binary (sync driver) — worker is not async.
DATABASE_URL may arrive as postgresql+asyncpg:// (from portal-api env) or
postgresql+psycopg2://; we normalise to psycopg2 in make_engine().
"""
from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from portal_worker.config import Settings


def make_engine(settings: Settings) -> Engine:
    """Создаёт sync Engine, заменяя asyncpg-драйвер на psycopg2."""
    url = str(settings.database_url)
    # Нормализуем к psycopg2 независимо от того, что передали в DATABASE_URL
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    url = url.replace("postgresql://", "postgresql+psycopg2://")
    return create_engine(url, pool_pre_ping=True, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Возвращает sync sessionmaker."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
