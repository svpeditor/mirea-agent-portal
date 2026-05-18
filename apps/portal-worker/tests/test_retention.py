"""Тесты retention-чистки файлов завершённых job'ов.

Контракт: файлы (вход/выход) и строки job_files job'ов в терминальном
статусе старше retention_days удаляются; сам job + события остаются;
running/queued и свежие не трогаются; идемпотентно.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from portal_worker.services.retention import purge_expired_job_files


def _db_url(pg: PostgresContainer) -> str:
    return pg.get_connection_url().replace(
        "postgresql://", "postgresql+psycopg2://"
    )


def _insert_job(
    pg: PostgresContainer,
    root: Path,
    *,
    status: str,
    finished_days_ago: int | None,
    with_files: bool,
    tag: str,
) -> str:
    engine = create_engine(_db_url(pg))
    with engine.begin() as conn:
        uid = conn.execute(text("""
            INSERT INTO users (email, password_hash, display_name)
            VALUES (:e,'x','U') ON CONFLICT (email) DO UPDATE SET display_name='U'
            RETURNING id
        """), {"e": f"ret-{tag}@x.x"}).scalar_one()
        tab = conn.execute(text("""
            INSERT INTO tabs (slug,name) VALUES ('ret','Ret')
            ON CONFLICT (slug) DO UPDATE SET name='Ret' RETURNING id
        """)).scalar_one()
        aid = conn.execute(text("""
            INSERT INTO agents (slug,name,short_description,tab_id,git_url,created_by_user_id)
            VALUES (:s,'A','d',:t,'https://g',:u)
            ON CONFLICT (slug) DO UPDATE SET name='A' RETURNING id
        """), {"s": f"ret-a-{tag}", "t": tab, "u": uid}).scalar_one()
        vid = conn.execute(text("""
            INSERT INTO agent_versions
              (agent_id,git_sha,git_ref,manifest_jsonb,manifest_version,status,created_by_user_id)
            VALUES (:a,:sha,'main','{}','1','ready',:u) RETURNING id
        """), {"a": aid, "sha": f"sha-{tag}", "u": uid}).scalar_one()
        finished = (
            None if finished_days_ago is None
            else datetime.now(timezone.utc) - timedelta(days=finished_days_ago)
        )
        jid = conn.execute(text("""
            INSERT INTO jobs (agent_version_id,created_by_user_id,status,finished_at)
            VALUES (:v,:u,:st,:f) RETURNING id
        """), {"v": vid, "u": uid, "st": status, "f": finished}).scalar_one()
        conn.execute(text("""
            INSERT INTO job_events (job_id,seq,event_type,payload_jsonb)
            VALUES (:j,1,'started','{}')
        """), {"j": jid})
        if with_files:
            conn.execute(text("""
                INSERT INTO job_files (job_id,kind,filename,size_bytes,sha256,storage_key)
                VALUES (:j,'output','report.docx',10,'abc',:k)
            """), {"j": jid, "k": f"{jid}/output/report.docx"})
    engine.dispose()
    # материализуем директорию job'а на диске
    d = root / str(jid)
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "input").mkdir(parents=True, exist_ok=True)
    (d / "output" / "report.docx").write_bytes(b"x" * 10)
    return str(jid)


def _files_count(pg: PostgresContainer, jid: str) -> int:
    engine = create_engine(_db_url(pg))
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM job_files WHERE job_id=:j"), {"j": jid}
        ).scalar_one()
    engine.dispose()
    return int(n)


def _job_exists(pg: PostgresContainer, jid: str) -> bool:
    engine = create_engine(_db_url(pg))
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM jobs WHERE id=:j"), {"j": jid}
        ).scalar_one()
    engine.dispose()
    return int(n) == 1


def test_purges_expired_job_with_files(
    db_with_schema: None, pg_container: PostgresContainer, tmp_path: Path
) -> None:
    jid = _insert_job(
        pg_container, tmp_path, status="ready",
        finished_days_ago=11, with_files=True, tag="exp1",
    )
    purged = purge_expired_job_files(_db_url(pg_container), tmp_path, retention_days=10)

    assert jid in purged
    assert not (tmp_path / jid).exists()
    assert _files_count(pg_container, jid) == 0
    assert _job_exists(pg_container, jid)  # сам job — история, остаётся


def test_keeps_recent_job(
    db_with_schema: None, pg_container: PostgresContainer, tmp_path: Path
) -> None:
    jid = _insert_job(
        pg_container, tmp_path, status="ready",
        finished_days_ago=2, with_files=True, tag="fresh",
    )
    purged = purge_expired_job_files(_db_url(pg_container), tmp_path, retention_days=10)

    assert jid not in purged
    assert (tmp_path / jid).exists()
    assert _files_count(pg_container, jid) == 1


def test_keeps_running_job(
    db_with_schema: None, pg_container: PostgresContainer, tmp_path: Path
) -> None:
    jid = _insert_job(
        pg_container, tmp_path, status="running",
        finished_days_ago=None, with_files=False, tag="run",
    )
    purged = purge_expired_job_files(_db_url(pg_container), tmp_path, retention_days=10)

    assert jid not in purged
    assert (tmp_path / jid).exists()


def test_purges_failed_job_without_files(
    db_with_schema: None, pg_container: PostgresContainer, tmp_path: Path
) -> None:
    """Упавший job (0 job_files) — input-папка всё равно должна удалиться."""
    jid = _insert_job(
        pg_container, tmp_path, status="failed",
        finished_days_ago=15, with_files=False, tag="failnofiles",
    )
    purged = purge_expired_job_files(_db_url(pg_container), tmp_path, retention_days=10)

    assert jid in purged
    assert not (tmp_path / jid).exists()


def test_idempotent(
    db_with_schema: None, pg_container: PostgresContainer, tmp_path: Path
) -> None:
    _insert_job(
        pg_container, tmp_path, status="ready",
        finished_days_ago=20, with_files=True, tag="idem",
    )
    first = purge_expired_job_files(_db_url(pg_container), tmp_path, retention_days=10)
    second = purge_expired_job_files(_db_url(pg_container), tmp_path, retention_days=10)

    assert len(first) == 1
    assert second == []  # второй проход — ничего не делает, без ошибок
