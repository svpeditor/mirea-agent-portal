"""GET /api/jobs/{id}/outputs/{file_id}."""
from __future__ import annotations

import copy
import uuid
from unittest.mock import MagicMock

import pytest

from portal_api.models import JobFile
from portal_api.services.file_store import LocalDiskFileStore
from tests.factories import make_agent, make_agent_version, make_tab


def _mock_enqueuer():
    m = MagicMock()
    m.enqueue_run = MagicMock()
    return m


def _make_settings_override(tmp_path):
    from portal_api.config import get_settings
    base = get_settings()
    s = copy.copy(base)
    object.__setattr__(s, "file_store_local_root", tmp_path)
    return lambda: s


async def _login(client, user):
    resp = await client.post(
        "/api/auth/login", json={"email": user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200


async def _ready_agent_with_job(client, db, admin_user, slug):
    from portal_api.deps import get_job_enqueuer
    from portal_api.main import app

    tab = await make_tab(db, slug=f"out-{slug}", name="T", order_idx=1)
    agent = await make_agent(db, slug=slug, tab_id=tab.id,
                              created_by_user_id=admin_user.id, enabled=True)
    v = await make_agent_version(db, agent_id=agent.id,
                                  created_by_user_id=admin_user.id, status="ready")
    agent.current_version_id = v.id
    await db.commit()
    app.dependency_overrides[get_job_enqueuer] = lambda: _mock_enqueuer()
    try:
        r = await client.post(f"/api/agents/{slug}/jobs", data={"params": "{}"})
    finally:
        app.dependency_overrides.pop(get_job_enqueuer, None)
    return uuid.UUID(r.json()["job"]["id"])


@pytest.mark.asyncio
async def test_download_output_happy_path(user_client, db, admin_user, tmp_path) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="dl-ok")

        # Write a real file into the store
        fs = LocalDiskFileStore(root=tmp_path)
        key = f"{job_id}/output/result.txt"
        content = b"hello output"

        async def _data():
            yield content

        size, sha = await fs.put(key, _data())

        file_id = uuid.uuid4()
        db.add(JobFile(
            id=file_id, job_id=job_id, kind="output",
            filename="result.txt", content_type="text/plain",
            size_bytes=size, sha256=sha, storage_key=key,
        ))
        await db.commit()

        resp = await user_client.get(f"/api/jobs/{job_id}/outputs/{file_id}")
        assert resp.status_code == 200
        assert resp.content == content
        assert resp.headers["content-type"].startswith("text/plain")
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_download_output_wrong_job_404(user_client, db, admin_user, tmp_path) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="dl-wj")

        # file_id belongs to a different job_id (not the user's job)
        # just use a random UUID that has no JobFile row for the target job_id
        file_id = uuid.uuid4()

        # Request file_id that doesn't belong to job_id
        resp = await user_client.get(f"/api/jobs/{job_id}/outputs/{file_id}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_outputs_returns_only_outputs(
    user_client, db, admin_user, tmp_path,
) -> None:
    """GET /api/jobs/{id}/outputs возвращает только output-файлы (не input).

    Сортировка по created_at, filename — детерминированный порядок для UI.
    """
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="ls-out")

        # один input-файл (не должен попасть в outputs)
        db.add(JobFile(
            id=uuid.uuid4(), job_id=job_id, kind="input",
            filename="works.zip", content_type="application/zip",
            size_bytes=10, sha256="x" * 64, storage_key=f"{job_id}/input/works.zip",
        ))
        # два output-файла
        out1 = uuid.uuid4()
        db.add(JobFile(
            id=out1, job_id=job_id, kind="output",
            filename="a-report.docx", content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            size_bytes=100, sha256="a" * 64, storage_key=f"{job_id}/output/a-report.docx",
        ))
        out2 = uuid.uuid4()
        db.add(JobFile(
            id=out2, job_id=job_id, kind="output",
            filename="b-summary.json", content_type="application/json",
            size_bytes=50, sha256="b" * 64, storage_key=f"{job_id}/output/b-summary.json",
        ))
        await db.commit()

        resp = await user_client.get(f"/api/jobs/{job_id}/outputs")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        names = [f["filename"] for f in body]
        assert "a-report.docx" in names
        assert "b-summary.json" in names
        # input-файла не должно быть
        assert "works.zip" not in names
        # JobFileOut shape
        first = body[0]
        expected = {"id", "kind", "filename", "content_type", "size_bytes", "sha256", "created_at"}
        assert expected.issubset(first.keys())
        assert first["kind"] == "output"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_outputs_empty_when_no_files(
    user_client, db, admin_user, tmp_path,
) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="ls-empty")
        resp = await user_client.get(f"/api/jobs/{job_id}/outputs")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_outputs_other_user_404(
    user_client, admin_client, db, admin_user, regular_user, tmp_path,
) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        await _login(user_client, admin_user)
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="ls-other")
        db.add(JobFile(
            id=uuid.uuid4(), job_id=job_id, kind="output",
            filename="r.txt", content_type="text/plain",
            size_bytes=10, sha256="x" * 64, storage_key=f"{job_id}/output/r.txt",
        ))
        await db.commit()

        # regular пытается получить список — 404
        await _login(user_client, regular_user)
        resp = await user_client.get(f"/api/jobs/{job_id}/outputs")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_outputs_unknown_job_404(user_client, db, admin_user, tmp_path) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        fake_id = uuid.uuid4()
        resp = await user_client.get(f"/api/jobs/{fake_id}/outputs")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_download_output_other_user_404(
    user_client, admin_client, db, admin_user, regular_user, tmp_path,
) -> None:
    from portal_api.deps import get_settings
    from portal_api.main import app

    app.dependency_overrides[get_settings] = _make_settings_override(tmp_path)
    try:
        # admin creates the job (re-login to admin)
        await _login(user_client, admin_user)
        job_id = await _ready_agent_with_job(user_client, db, admin_user, slug="dl-ou")

        fs = LocalDiskFileStore(root=tmp_path)
        key = f"{job_id}/output/f.txt"

        async def _data():
            yield b"data"

        size, sha = await fs.put(key, _data())

        file_id = uuid.uuid4()
        db.add(JobFile(
            id=file_id, job_id=job_id, kind="output",
            filename="f.txt", content_type="text/plain",
            size_bytes=size, sha256=sha, storage_key=key,
        ))
        await db.commit()

        # regular user tries to download admin's job output
        await _login(user_client, regular_user)
        resp = await user_client.get(f"/api/jobs/{job_id}/outputs/{file_id}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)
