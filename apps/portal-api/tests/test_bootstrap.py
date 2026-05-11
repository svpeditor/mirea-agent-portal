"""Бутстрап первого админа при пустой БД."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.bootstrap import bootstrap_admin
from portal_api.config import Settings
from portal_api.core.security import verify_password
from portal_api.models import User, UserQuota


@pytest.mark.asyncio
async def test_creates_admin_on_empty_db(db: AsyncSession) -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://stub:stub@stub/stub",
        jwt_secret="x" * 64,  # type: ignore[arg-type]
        initial_admin_email="admin@example.com",
        initial_admin_password="StrongPass123",  # type: ignore[arg-type]
    )

    await bootstrap_admin(db, settings)

    res = await db.execute(select(User).where(User.email == "admin@example.com"))
    admin = res.scalar_one()
    assert admin.role == "admin"
    assert admin.display_name == "Admin"
    assert verify_password("StrongPass123", admin.password_hash)


@pytest.mark.asyncio
async def test_creates_user_quota_for_bootstrap_admin(db: AsyncSession) -> None:
    """Без UserQuota admin падает 500 на первом же LLM-вызове (NoResultFound)."""
    settings = Settings(
        database_url="postgresql+asyncpg://stub:stub@stub/stub",
        jwt_secret="x" * 64,  # type: ignore[arg-type]
        initial_admin_email="admin@example.com",
        initial_admin_password="StrongPass123",  # type: ignore[arg-type]
    )

    await bootstrap_admin(db, settings)

    admin = (
        await db.execute(select(User).where(User.email == "admin@example.com"))
    ).scalar_one()
    quota = (
        await db.execute(select(UserQuota).where(UserQuota.user_id == admin.id))
    ).scalar_one_or_none()
    assert quota is not None, "bootstrap_admin должен создавать UserQuota"
    assert quota.monthly_limit_usd == Decimal("999999.9999")
    assert quota.per_job_cap_usd == settings.llm_default_per_job_cap_usd


@pytest.mark.asyncio
async def test_raises_when_empty_db_and_no_env(db: AsyncSession) -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://stub:stub@stub/stub",
        jwt_secret="x" * 64,  # type: ignore[arg-type]
        initial_admin_email=None,
        initial_admin_password=None,
    )
    with pytest.raises(RuntimeError, match="INITIAL_ADMIN"):
        await bootstrap_admin(db, settings)


@pytest.mark.asyncio
async def test_does_nothing_when_users_exist(db: AsyncSession, regular_user: User) -> None:
    """Если в БД хоть один юзер — ENV игнорируется."""
    settings = Settings(
        database_url="postgresql+asyncpg://stub:stub@stub/stub",
        jwt_secret="x" * 64,  # type: ignore[arg-type]
        initial_admin_email="admin@example.com",
        initial_admin_password="OtherPass",  # type: ignore[arg-type]
    )

    await bootstrap_admin(db, settings)

    # Не должно быть админа из ENV
    res = await db.execute(select(User).where(User.email == "admin@example.com"))
    assert res.scalar_one_or_none() is None
