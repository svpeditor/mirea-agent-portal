"""LocalDiskFileStore — put/get/open_path/delete + sha256."""
from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from portal_api.services.file_store import LocalDiskFileStore


@pytest.mark.asyncio
async def test_put_returns_size_and_sha256(tmp_path: Path) -> None:
    fs = LocalDiskFileStore(root=tmp_path)
    data = b"hello world"
    expected_sha = hashlib.sha256(data).hexdigest()

    async def chunks() -> AsyncIterator[bytes]:
        yield data

    size, sha = await fs.put("job-1/input/a.txt", chunks())
    assert size == len(data)
    assert sha == expected_sha
    assert (tmp_path / "job-1/input/a.txt").exists()


@pytest.mark.asyncio
async def test_get_streams_back_bytes(tmp_path: Path) -> None:
    fs = LocalDiskFileStore(root=tmp_path)

    async def chunks() -> AsyncIterator[bytes]:
        yield b"foo"
        yield b"bar"

    await fs.put("job-2/input/x", chunks())
    out = b""
    async for chunk in fs.get("job-2/input/x"):
        out += chunk
    assert out == b"foobar"


@pytest.mark.asyncio
async def test_open_path_returns_absolute(tmp_path: Path) -> None:
    fs = LocalDiskFileStore(root=tmp_path)

    async def chunks() -> AsyncIterator[bytes]:
        yield b"x"

    await fs.put("job-3/input/y", chunks())
    p = await fs.open_path("job-3/input/y")
    assert p.is_absolute()
    assert p.read_bytes() == b"x"


@pytest.mark.asyncio
async def test_delete_removes_file(tmp_path: Path) -> None:
    fs = LocalDiskFileStore(root=tmp_path)

    async def chunks() -> AsyncIterator[bytes]:
        yield b"x"

    await fs.put("job-4/input/y", chunks())
    await fs.delete("job-4/input/y")
    assert not (tmp_path / "job-4/input/y").exists()


@pytest.mark.asyncio
async def test_put_rejects_path_traversal(tmp_path: Path) -> None:
    fs = LocalDiskFileStore(root=tmp_path)

    async def chunks() -> AsyncIterator[bytes]:
        yield b"x"

    with pytest.raises(ValueError, match="path traversal"):
        await fs.put("../etc/passwd", chunks())
