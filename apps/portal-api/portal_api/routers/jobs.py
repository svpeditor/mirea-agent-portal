# ruff: noqa: B008
"""Public jobs endpoints."""
from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from redis import Redis as SyncRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from portal_api.config import Settings, get_settings
from portal_api.core.exceptions import (
    InputFilenameInvalidError,
    InputsTooLargeError,
    ParamsInvalidJsonError,
)
from portal_api.deps import get_current_user, get_db, get_job_enqueuer
from portal_api.models import Agent, AgentVersion, JobFile, User
from portal_api.schemas.job import (
    JobAgentBrief,
    JobCancelOut,
    JobCreatedOut,
    JobDetailOut,
    JobEventOut,
    JobFileOut,
    JobListItemOut,
)
from portal_api.services import job_event_service, job_service
from portal_api.services.file_store import LocalDiskFileStore
from portal_api.services.job_enqueue import JobEnqueuer

router = APIRouter(tags=["jobs"])

_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\-/]+$")
_INPUT_FIELD_RE = re.compile(r"^inputs\[(?P<name>.+)\]$")


def _validate_input_filename(filename: str) -> None:
    if filename.startswith("/") or ".." in filename or not _FILENAME_RE.match(filename):
        raise InputFilenameInvalidError()


@router.post("/agents/{slug}/jobs", status_code=202)
async def create_job(
    slug: str,
    request: Request,
    params: str = Form(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    enqueuer: JobEnqueuer = Depends(get_job_enqueuer),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        params_dict = json.loads(params)
        if not isinstance(params_dict, dict):
            raise ValueError("params must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        raise ParamsInvalidJsonError() from exc

    form = await request.form()
    inputs: list[tuple[str, UploadFile]] = []
    for field, value in form.multi_items():
        m = _INPUT_FIELD_RE.match(field)
        if not m:
            continue
        if not isinstance(value, UploadFile):
            continue
        filename = m.group("name")
        _validate_input_filename(filename)
        inputs.append((filename, value))

    # Создать job (валидирует agent + version; quota check + ephemeral token при runtime.llm)
    job, ephemeral_plaintext = await job_service.create_job(
        db, agent_slug=slug, params=params_dict, user_id=user.id,
    )

    # Стримим каждый файл в FileStore
    file_store = LocalDiskFileStore(root=settings.file_store_local_root)
    total_bytes = 0
    written_keys: list[str] = []
    for filename, upload in inputs:
        async def _chunks(_u: UploadFile = upload) -> AsyncIterator[bytes]:
            while True:
                chunk = await _u.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

        key = f"{job.id}/input/{filename}"
        size, sha = await file_store.put(key, _chunks())
        written_keys.append(key)
        total_bytes += size
        if total_bytes > settings.max_job_input_bytes:
            for k in written_keys:
                await file_store.delete(k)
            await db.rollback()
            raise InputsTooLargeError()
        db.add(JobFile(
            id=uuid.uuid4(), job_id=job.id, kind="input",
            filename=filename, content_type=upload.content_type,
            size_bytes=size, sha256=sha, storage_key=key,
        ))

    await db.commit()
    await db.refresh(job)

    enqueuer.enqueue_run(
        job.id,
        timeout_seconds=settings.job_timeout_seconds + 60,
        ephemeral_token=ephemeral_plaintext,
    )

    return {
        "job": JobCreatedOut(
            id=job.id, status=job.status, agent_slug=slug,
        ).model_dump(mode="json"),
    }


@router.get("/jobs", response_model=list[JobListItemOut])
async def list_jobs(
    limit: int = 20,
    before: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[JobListItemOut]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1..100")
    jobs = await job_service.list_for_user(db, user, limit=limit, before=before)
    return [JobListItemOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobDetailOut)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobDetailOut:
    from portal_api.core.exceptions import JobNotFoundError

    job = await job_service.get_job_for_user(db, job_id, user)
    if job is None:
        raise JobNotFoundError()
    agent_row = (await db.execute(
        select(Agent.slug, Agent.name)
        .join(AgentVersion, AgentVersion.id == job.agent_version_id)
        .where(Agent.id == AgentVersion.agent_id)
    )).first()
    if agent_row is None:
        raise HTTPException(status_code=404, detail={"error_code": "job_not_found"})
    count, last_seq = await job_event_service.count_for_job(db, job.id)
    return JobDetailOut(
        id=job.id, status=job.status, agent_version_id=job.agent_version_id,
        agent=JobAgentBrief(slug=agent_row.slug, name=agent_row.name),
        params=job.params_jsonb,
        started_at=job.started_at, finished_at=job.finished_at,
        exit_code=job.exit_code, error_code=job.error_code, error_msg=job.error_msg,
        output_summary=job.output_summary_jsonb,
        events_count=count, last_event_seq=last_seq,
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}/events", response_model=list[JobEventOut])
async def list_job_events(
    job_id: uuid.UUID,
    since: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    from portal_api.core.exceptions import JobNotFoundError

    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be 1..1000")
    job = await job_service.get_job_for_user(db, job_id, user)
    if job is None:
        raise JobNotFoundError()
    return await job_event_service.list_since(db, job_id, since=since, limit=limit)


@router.get("/jobs/{job_id}/outputs", response_model=list[JobFileOut])
async def list_job_outputs(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[JobFileOut]:
    """Список output-файлов job. Кому виден job, тому виден список (owner или admin)."""
    from portal_api.core.exceptions import JobNotFoundError

    job = await job_service.get_job_for_user(db, job_id, user)
    if job is None:
        raise JobNotFoundError()
    rows = (await db.execute(
        select(JobFile)
        .where(JobFile.job_id == job_id, JobFile.kind == "output")
        .order_by(JobFile.created_at, JobFile.filename)
    )).scalars().all()
    return [JobFileOut.model_validate(r) for r in rows]


@router.get("/jobs/{job_id}/outputs/{file_id}")
async def download_job_output(
    job_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    from portal_api.core.exceptions import JobNotFoundError

    job = await job_service.get_job_for_user(db, job_id, user)
    if job is None:
        raise JobNotFoundError()
    file_row = (await db.execute(
        select(JobFile).where(
            JobFile.id == file_id,
            JobFile.job_id == job_id,
            JobFile.kind == "output",
        )
    )).scalar_one_or_none()
    if file_row is None:
        raise HTTPException(status_code=404, detail={"error_code": "file_not_found"})

    fs = LocalDiskFileStore(root=settings.file_store_local_root)
    return StreamingResponse(
        fs.get(file_row.storage_key),
        media_type=file_row.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_row.filename}"',
            "Content-Length": str(file_row.size_bytes),
        },
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobCancelOut)
async def cancel_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> JobCancelOut:
    from portal_api.core.exceptions import JobNotFoundError

    job = await job_service.cancel_job(db, job_id, user)
    if job is None:
        raise JobNotFoundError()
    if job.status == "running":
        redis = SyncRedis.from_url(str(settings.redis_url))
        redis.set(f"job:{job_id}:cancel", "1", ex=3600)
        redis.close()
    return JobCancelOut(id=job.id, status=job.status)
