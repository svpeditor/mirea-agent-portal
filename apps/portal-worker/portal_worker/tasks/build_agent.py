"""RQ-zadacha build_agent_version + recover_orphaned_builds."""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog
from sqlalchemy import text

from portal_worker.builder.docker_build import (
    build_image,
    image_size_bytes,
    remove_image,
)
from portal_worker.builder.dockerfile_gen import generate_dockerfile
from portal_worker.builder.git_clone import clone_at_sha
from portal_worker.builder.manifest_loader import load_and_validate_manifest
from portal_worker.config import get_settings
from portal_worker.core.exceptions import BuildError
from portal_worker.db import make_engine, make_session_factory

_BUILD_ROOT = Path("/tmp")  # noqa: S108


def recover_orphaned_builds() -> None:
    """At worker start: mark all 'building' versions as 'failed: worker_restart'."""
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    log = structlog.get_logger()
    with session_factory() as session:
        result = session.execute(text("""
            UPDATE agent_versions
            SET status = 'failed', build_error = 'worker_restart',
                build_finished_at = :now
            WHERE status = 'building'
            RETURNING id
        """), {"now": datetime.now(UTC)})
        ids = [r[0] for r in result]
        session.commit()
    if ids:
        log.warning("recovered_orphaned_builds", count=len(ids))
    # Clean up stale /tmp/portal-build-* directories
    for stale in _BUILD_ROOT.glob("portal-build-*"):
        shutil.rmtree(stale, ignore_errors=True)
    engine.dispose()


def _short_sha(sha: str) -> str:
    return sha[:7]


def build_agent_version(version_id: str) -> None:
    """Build Docker image for the specified agent_version."""
    log = structlog.get_logger().bind(version_id=version_id)
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    vid = uuid.UUID(version_id)
    tempdir = _BUILD_ROOT / f"portal-build-{vid}"

    try:
        # 0. Pre-flight: atomic lock status='pending_build' -> 'building'
        # UPDATE...FROM...RETURNING collapses SELECT+UPDATE into one statement,
        # eliminating the TOCTOU race where two workers both pass the status guard.
        with session_factory() as session:
            row = session.execute(text("""
                UPDATE agent_versions av
                SET status='building', build_started_at=:now,
                    build_log=NULL, build_error=NULL, build_finished_at=NULL
                FROM agents a
                WHERE av.id=:vid AND av.status='pending_build' AND a.id = av.agent_id
                RETURNING av.id, av.git_sha, a.git_url, a.slug
            """), {"vid": vid, "now": datetime.now(UTC)}).first()
            session.commit()
            if row is None:
                # Either version doesn't exist or status != 'pending_build' (raced or already done)
                log.info("version_not_pending_or_missing")
                engine.dispose()
                return

            expected_sha = row.git_sha
            git_url = row.git_url
            agent_slug = row.slug

        # 1. Clone
        repo_dir = tempdir / "repo"
        actual_sha = clone_at_sha(
            git_url, git_ref=expected_sha,
            target_dir=repo_dir,
            max_repo_size_bytes=settings.build_max_repo_size_bytes,
            clone_timeout=settings.build_clone_timeout_seconds,
        )
        if actual_sha != expected_sha:
            raise BuildError("clone_failed",
                             f"sha mismatch: cloned {actual_sha} vs expected {expected_sha}")

        # 2. Manifest
        manifest = load_and_validate_manifest(
            repo_dir=repo_dir, agent_slug=agent_slug,
            allowed_base_images=settings.allowed_base_images,
        )

        # 3. Build context: copy repo + SDK
        build_dir = tempdir / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        shutil.copytree(repo_dir, build_dir)
        shutil.copytree(settings.portal_sdk_path, build_dir / ".portal-sdk")

        # 4. Dockerfile
        dockerfile_text = generate_dockerfile(manifest)
        (build_dir / "Dockerfile.portal").write_text(dockerfile_text, encoding="utf-8")

        # 5-6. Build + size check
        tag = f"portal/agent-{agent_slug}:v{_short_sha(actual_sha)}"
        try:
            build_log = build_image(
                context_dir=build_dir, dockerfile_name="Dockerfile.portal",
                tag=tag, timeout_seconds=settings.build_timeout_seconds,
                memory_limit_bytes=settings.build_memory_limit_bytes,
            )
        except BuildError as exc:
            with session_factory() as session:
                session.execute(text("""
                    UPDATE agent_versions
                    SET status='failed', build_error=:err, build_log=:log,
                        build_finished_at=:now
                    WHERE id=:vid
                """), {"err": exc.code, "log": exc.log[-1_000_000:],
                       "vid": vid, "now": datetime.now(UTC)})
                session.commit()
            return

        size = image_size_bytes(tag)
        if size > settings.build_max_image_size_bytes:
            remove_image(tag)
            with session_factory() as session:
                session.execute(text("""
                    UPDATE agent_versions
                    SET status='failed', build_error='image_too_large',
                        build_log=:log, build_finished_at=:now
                    WHERE id=:vid
                """), {"log": build_log[-1_000_000:], "vid": vid,
                       "now": datetime.now(UTC)})
                session.commit()
            return

        # 8. Finalize
        with session_factory() as session:
            # Write manifest snapshot again in case the admin endpoint wrote
            # an earlier placeholder with minimal validation
            manifest_jsonb = json.loads(manifest.model_dump_json())
            session.execute(text("""
                UPDATE agent_versions
                SET status='ready', docker_image_tag=:tag,
                    build_log=:log, build_finished_at=:now,
                    manifest_jsonb=:m, manifest_version=:mv
                WHERE id=:vid
            """), {
                "tag": tag, "log": build_log[-1_000_000:],
                "vid": vid, "now": datetime.now(UTC),
                "m": json.dumps(manifest_jsonb), "mv": manifest.version,
            })
            session.commit()
        log.info("build_succeeded", tag=tag, image_size=size)

    except BuildError as exc:
        log.warning("build_error", code=exc.code, log=exc.log[:500])
        with session_factory() as session:
            session.execute(text("""
                UPDATE agent_versions
                SET status='failed', build_error=:err, build_log=:log,
                    build_finished_at=:now
                WHERE id=:vid
            """), {"err": exc.code, "log": exc.log[-1_000_000:],
                   "vid": vid, "now": datetime.now(UTC)})
            session.commit()
    except Exception as exc:  # pragma: no cover — defensive
        log.error("build_unexpected", exc_info=True)
        with session_factory() as session:
            session.execute(text("""
                UPDATE agent_versions
                SET status='failed', build_error='docker_error', build_log=:log,
                    build_finished_at=:now
                WHERE id=:vid
            """), {"log": str(exc)[:1_000_000], "vid": vid,
                   "now": datetime.now(UTC)})
            session.commit()
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
        engine.dispose()
