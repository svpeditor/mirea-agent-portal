"""Тесты миграции 0002_registry — таблицы tabs, agents, agent_versions."""
from __future__ import annotations

import pytest
from sqlalchemy import inspect, text


@pytest.mark.asyncio
async def test_tables_exist(db_engine) -> None:  # type: ignore[no-untyped-def]
    """После apply миграций должны быть 3 новые таблицы."""
    async with db_engine.connect() as conn:
        names = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    assert "tabs" in names
    assert "agents" in names
    assert "agent_versions" in names


@pytest.mark.asyncio
async def test_agent_versions_status_check_constraint(db_engine) -> None:  # type: ignore[no-untyped-def]
    """status CHECK ограничивает 4 значения."""
    sha = "a" * 40

    # Создаём минимально нужные FK, чтобы дойти до проверки CHECK
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, display_name, role,
                                   monthly_budget_usd, created_at, updated_at)
                VALUES (gen_random_uuid(), 'a@example.com', 'x', 'A', 'admin',
                        5.00, now(), now())
                """
            )
        )
        admin_id = (
            await conn.execute(
                text("SELECT id FROM users WHERE email='a@example.com'")
            )
        ).scalar_one()

        await conn.execute(
            text(
                """
                INSERT INTO tabs (id, slug, name, order_idx, is_system,
                                  created_at, updated_at)
                VALUES (gen_random_uuid(), 'sci', 'Sci', 0, false, now(), now())
                """
            )
        )
        tab_id = (
            await conn.execute(text("SELECT id FROM tabs WHERE slug='sci'"))
        ).scalar_one()

        await conn.execute(
            text(
                """
                INSERT INTO agents (id, slug, name, short_description, tab_id,
                                    enabled, git_url, created_by_user_id,
                                    created_at, updated_at)
                VALUES (gen_random_uuid(), 'a1', 'A1', 'desc', :tab, false,
                        'https://x.example.com/r.git', :uid, now(), now())
                """
            ),
            {"tab": tab_id, "uid": admin_id},
        )
        agent_id = (
            await conn.execute(text("SELECT id FROM agents WHERE slug='a1'"))
        ).scalar_one()

    # invalid status — должен упасть на CHECK
    async with db_engine.begin() as conn:
        with pytest.raises(Exception, match="status"):
            await conn.execute(
                text(
                    """
                    INSERT INTO agent_versions (id, agent_id, git_sha, git_ref,
                        manifest_jsonb, manifest_version, status,
                        created_by_user_id, created_at)
                    VALUES (gen_random_uuid(), :aid, :sha, 'main', '{}'::jsonb,
                            '0.1.0', 'invalid_status', :uid, now())
                    """
                ),
                {"aid": agent_id, "sha": sha, "uid": admin_id},
            )


@pytest.mark.asyncio
async def test_unique_agent_version_per_sha(db_engine) -> None:  # type: ignore[no-untyped-def]
    """UNIQUE (agent_id, git_sha)."""
    sha = "f" * 40

    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, display_name, role,
                                   monthly_budget_usd, created_at, updated_at)
                VALUES (gen_random_uuid(), 'b@example.com', 'x', 'B', 'admin',
                        5.00, now(), now())
                """
            )
        )
        admin_id = (
            await conn.execute(
                text("SELECT id FROM users WHERE email='b@example.com'")
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO tabs (id, slug, name, order_idx, is_system,
                                  created_at, updated_at)
                VALUES (gen_random_uuid(), 'sci2', 'Sci', 0, false, now(), now())
                """
            )
        )
        tab_id = (
            await conn.execute(text("SELECT id FROM tabs WHERE slug='sci2'"))
        ).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO agents (id, slug, name, short_description, tab_id,
                                    enabled, git_url, created_by_user_id,
                                    created_at, updated_at)
                VALUES (gen_random_uuid(), 'a2', 'A2', 'desc', :tab, false,
                        'https://x.example.com/r.git', :uid, now(), now())
                """
            ),
            {"tab": tab_id, "uid": admin_id},
        )
        agent_id = (
            await conn.execute(text("SELECT id FROM agents WHERE slug='a2'"))
        ).scalar_one()

        await conn.execute(
            text(
                """
                INSERT INTO agent_versions (id, agent_id, git_sha, git_ref,
                    manifest_jsonb, manifest_version, status,
                    created_by_user_id, created_at)
                VALUES (gen_random_uuid(), :aid, :sha, 'main', '{}'::jsonb,
                        '0.1.0', 'ready', :uid, now())
                """
            ),
            {"aid": agent_id, "sha": sha, "uid": admin_id},
        )

    async with db_engine.begin() as conn:
        with pytest.raises(Exception, match="agent_versions_agent_id_git_sha"):
            await conn.execute(
                text(
                    """
                    INSERT INTO agent_versions (id, agent_id, git_sha, git_ref,
                        manifest_jsonb, manifest_version, status,
                        created_by_user_id, created_at)
                    VALUES (gen_random_uuid(), :aid, :sha, 'main', '{}'::jsonb,
                            '0.1.0', 'ready', :uid, now())
                    """
                ),
                {"aid": agent_id, "sha": sha, "uid": admin_id},
            )


@pytest.mark.asyncio
async def test_downgrade(db_engine, alembic_config) -> None:  # type: ignore[no-untyped-def]
    """alembic downgrade 0001_init удаляет три таблицы."""
    import asyncio

    from alembic import command

    try:
        # downgrade
        await asyncio.to_thread(command.downgrade, alembic_config, "0001_init")

        async with db_engine.connect() as conn:
            names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert "tabs" not in names
        assert "agents" not in names
        assert "agent_versions" not in names
    finally:
        # Возвращаем БД в head, чтобы не сломать другие тесты,
        # которые шарят session-scoped `_migrated`.
        await asyncio.to_thread(command.upgrade, alembic_config, "head")
