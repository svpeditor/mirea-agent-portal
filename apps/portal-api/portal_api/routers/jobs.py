# ruff: noqa: B008
"""Public jobs endpoints."""
from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from portal_api.config import Settings, get_settings
from portal_api.core.exceptions import (
    InputFilenameInvalidError,
    InputsTooLargeError,
    ParamsInvalidJsonError,
)
from portal_api.deps import get_current_user, get_db, get_job_enqueuer
from portal_api.models import JobFile, User
from portal_api.schemas.job import JobCreatedOut
from portal_api.services import job_service
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

    # Создать job (валидирует agent + version)
    job = await job_service.create_job(
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

    enqueuer.enqueue_run(job.id, timeout_seconds=settings.job_timeout_seconds + 60)

    return {
        "job": JobCreatedOut(
            id=job.id, status=job.status, agent_slug=slug,
        ).model_dump(mode="json"),
    }
