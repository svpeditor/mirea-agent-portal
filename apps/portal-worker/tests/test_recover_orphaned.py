"""Tests for recover_orphaned_builds."""
from __future__ import annotations

from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from portal_worker.tasks.build_agent import recover_orphaned_builds


def _insert_version(
    pg_container: PostgresContainer,
    *,
    status: str,
    git_sha: str = "abc123",
) -> str:
    """Insert a test agent_version row and return its id."""
    raw_url = pg_container.get_connection_url()
    db_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    engine = create_engine(db_url)
    with engine.begin() as conn:
        user_id = conn.execute(
            text("""
                INSERT INTO users (email, password_hash, display_name)
                VALUES (:email, 'x', 'Test User')
                ON CONFLICT (email) DO UPDATE SET display_name = 'Test User'
                RETURNING id
            """),
            {"email": f"test-{git_sha}@example.com"},
        ).scalar_one()

        tab_id = conn.execute(
            text("""
                INSERT INTO tabs (slug, name)
                VALUES ('default', 'Default')
                ON CONFLICT (slug) DO UPDATE SET name = 'Default'
                RETURNING id
            """),
        ).scalar_one()

        agent_id = conn.execute(
            text("""
                INSERT INTO agents
                    (slug, name, short_description, tab_id, git_url, created_by_user_id)
                VALUES (:slug, 'Test', 'desc', :tab_id, 'https://git', :uid)
                ON CONFLICT (slug) DO UPDATE SET name = 'Test'
                RETURNING id
            """),
            {"slug": f"agent-{git_sha}", "tab_id": tab_id, "uid": user_id},
        ).scalar_one()

        version_id = conn.execute(
            text("""
                INSERT INTO agent_versions
                    (agent_id, git_sha, git_ref, manifest_jsonb, manifest_version,
                     status, created_by_user_id)
                VALUES
                    (:agent_id, :git_sha, 'main', '{}', '1',
                     :status, :uid)
                RETURNING id
            """),
            {"agent_id": agent_id, "git_sha": git_sha, "status": status, "uid": user_id},
        ).scalar_one()

    engine.dispose()
    return str(version_id)


def _get_version(pg_container: PostgresContainer, version_id: str) -> dict[str, object]:
    raw_url = pg_container.get_connection_url()
    db_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT status, build_error, build_finished_at"
                " FROM agent_versions WHERE id = :id"
            ),
            {"id": version_id},
        ).mappings().one()
        result = dict(row)
    engine.dispose()
    return result


def test_recover_marks_building_as_failed(
    db_with_schema: None,
    pg_container: PostgresContainer,
) -> None:
    """A 'building' version must become 'failed' with build_error='worker_restart'."""
    version_id = _insert_version(pg_container, status="building", git_sha="sha-building-001")

    recover_orphaned_builds()

    row = _get_version(pg_container, version_id)
    assert row["status"] == "failed"
    assert row["build_error"] == "worker_restart"
    assert row["build_finished_at"] is not None


def test_recover_does_not_touch_other_statuses(
    db_with_schema: None,
    pg_container: PostgresContainer,
) -> None:
    """'ready' versions must not be touched by recover_orphaned_builds."""
    version_id = _insert_version(pg_container, status="ready", git_sha="sha-ready-001")

    recover_orphaned_builds()

    row = _get_version(pg_container, version_id)
    assert row["status"] == "ready"
