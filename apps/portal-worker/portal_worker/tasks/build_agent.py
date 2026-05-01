"""RQ tasks for building agent versions.

build_agent_version -- stub (Tasks 13-16).
recover_orphaned_builds -- called at worker startup.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text

from portal_worker.config import get_settings
from portal_worker.db import make_engine, make_session_factory

logger: structlog.BoundLogger = structlog.get_logger(__name__)


def recover_orphaned_builds() -> None:
    """Mark all 'building' versions as 'failed' on worker restart.

    'building' status means the previous worker died mid-build.
    """
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        result = session.execute(
            text("""
                UPDATE agent_versions
                SET
                    status = 'failed',
                    build_error = 'worker_restart',
                    build_finished_at = now()
                WHERE status = 'building'
                RETURNING id
            """)
        )
        rows = result.fetchall()
        session.commit()

    recovered_ids = [str(row[0]) for row in rows]
    if recovered_ids:
        logger.info(
            "recovered_orphaned_builds",
            count=len(recovered_ids),
            ids=recovered_ids,
        )
    engine.dispose()


def build_agent_version(version_id: str) -> None:
    """Stub -- implementation in Tasks 13-16.

    Sets 'pending_build' version to 'failed' with build_error='stub'.
    """
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        session.execute(
            text("""
                UPDATE agent_versions
                SET
                    status = 'failed',
                    build_error = 'stub',
                    build_finished_at = now()
                WHERE id = :version_id
                  AND status = 'pending_build'
            """),
            {"version_id": version_id},
        )
        session.commit()

    logger.info("build_agent_version_stub", version_id=version_id)
    engine.dispose()
