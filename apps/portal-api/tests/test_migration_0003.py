"""Миграция 0003 создаёт таблицы jobs/job_events/job_files."""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import inspect, text

from alembic import command


@pytest.mark.asyncio
async def test_upgrade_creates_three_tables(alembic_config, db_engine) -> None:  # type: ignore[no-untyped-def]
    await asyncio.to_thread(command.upgrade, alembic_config, "head")
    async with db_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    assert {"jobs", "job_events", "job_files"}.issubset(tables)


@pytest.mark.asyncio
async def test_jobs_status_check_constraint(alembic_config, db_engine) -> None:  # type: ignore[no-untyped-def]
    await asyncio.to_thread(command.upgrade, alembic_config, "head")
    async with db_engine.begin() as conn:
        uid = (await conn.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES ('jobs-mig@example.com', 'h', 'd') RETURNING id"
        ))).scalar_one()
        tid = (await conn.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('mig-tab', 'M') RETURNING id"
        ))).scalar_one()
        aid = (await conn.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES ('mig-a', 'A', 'd', :tid, 'https://x', :uid) RETURNING id"
        ), {"tid": tid, "uid": uid})).scalar_one()
        vid = (await conn.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, created_by_user_id) "
            "VALUES (:aid, :sha, 'main', '{}'::jsonb, '1.0', 'ready', :uid) "
            "RETURNING id"
        ), {"aid": aid, "sha": "f" * 40, "uid": uid})).scalar_one()

    async with db_engine.begin() as conn:
        with pytest.raises(Exception, match="jobs_status_check"):
            await conn.execute(text(
                "INSERT INTO jobs (agent_version_id, created_by_user_id, status) "
                "VALUES (:vid, :uid, 'invalid_status')"
            ), {"vid": vid, "uid": uid})


@pytest.mark.asyncio
async def test_job_files_unique_constraint(alembic_config, db_engine) -> None:  # type: ignore[no-untyped-def]
    await asyncio.to_thread(command.upgrade, alembic_config, "head")
    async with db_engine.begin() as conn:
        uid = (await conn.execute(text(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES ('jobs-mig2@example.com', 'h', 'd') RETURNING id"
        ))).scalar_one()
        tid = (await conn.execute(text(
            "INSERT INTO tabs (slug, name) VALUES ('mig-tab2', 'M') RETURNING id"
        ))).scalar_one()
        aid = (await conn.execute(text(
            "INSERT INTO agents (slug, name, short_description, tab_id, "
            "git_url, created_by_user_id) "
            "VALUES ('mig-a2', 'A', 'd', :tid, 'https://x', :uid) RETURNING id"
        ), {"tid": tid, "uid": uid})).scalar_one()
        vid = (await conn.execute(text(
            "INSERT INTO agent_versions (agent_id, git_sha, git_ref, "
            "manifest_jsonb, manifest_version, status, created_by_user_id) "
            "VALUES (:aid, :sha, 'main', '{}'::jsonb, '1.0', 'ready', :uid) "
            "RETURNING id"
        ), {"aid": aid, "sha": "e" * 40, "uid": uid})).scalar_one()
        jid = (await conn.execute(text(
            "INSERT INTO jobs (agent_version_id, created_by_user_id, status) "
            "VALUES (:vid, :uid, 'queued') RETURNING id"
        ), {"vid": vid, "uid": uid})).scalar_one()
        await conn.execute(text(
            "INSERT INTO job_files (job_id, kind, filename, size_bytes, sha256, storage_key) "
            "VALUES (:jid, 'input', 'a.txt', 1, 'sha', 'k')"
        ), {"jid": jid})

    async with db_engine.begin() as conn:
        with pytest.raises(Exception, match="job_files_job_kind_filename_key"):
            await conn.execute(text(
                "INSERT INTO job_files (job_id, kind, filename, size_bytes, sha256, storage_key) "
                "VALUES (:jid, 'input', 'a.txt', 1, 'sha', 'k2')"
            ), {"jid": jid})


@pytest.mark.asyncio
async def test_downgrade_drops_tables(alembic_config, db_engine) -> None:  # type: ignore[no-untyped-def]
    await asyncio.to_thread(command.upgrade, alembic_config, "head")
    try:
        await asyncio.to_thread(command.downgrade, alembic_config, "0002_registry")
        async with db_engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
        assert "jobs" not in tables
        assert "job_events" not in tables
        assert "job_files" not in tables
    finally:
        await asyncio.to_thread(command.upgrade, alembic_config, "head")
