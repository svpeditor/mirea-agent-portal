"""FileStore: storage abstraction for job input/output files.

Plan 1.2.3 provides LocalDiskFileStore only. S3 backend is a future plan.
"""
from __future__ import annotations

import hashlib
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import Protocol

import aiofiles


class FileStore(Protocol):
    async def put(
        self, key: str, data: AsyncIterable[bytes],
    ) -> tuple[int, str]:
        """Сохранить данные. Возвращает (size_bytes, sha256_hex)."""
        ...

    def get(self, key: str) -> AsyncIterable[bytes]:
        """Стримить данные обратно по 64KB кускам."""
        ...

    async def open_path(self, key: str) -> Path:
        """Абсолютный путь на host (для Docker bind-mount). Для local — прямой путь."""
        ...

    async def delete(self, key: str) -> None:
        """Удалить файл. Нет — no-op."""
        ...


class LocalDiskFileStore:
    """Хранит файлы на локальном диске под root/<key>."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _resolve(self, key: str) -> Path:
        # Защита от ../ traversal: после resolve путь должен оставаться под root
        candidate = (self._root / key).resolve()
        try:
            candidate.relative_to(self._root.resolve())
        except ValueError as exc:
            raise ValueError(f"path traversal not allowed: {key!r}") from exc
        return candidate

    async def put(
        self, key: str, data: AsyncIterable[bytes],
    ) -> tuple[int, str]:
        path = self._resolve(key)
        # mkdir с permissive perms: api=root, worker=uid 1000, agent-контейнер
        # тоже не root — все должны мочь писать. /var/portal-files mount shared.
        parent = path.parent
        parts_to_create = []
        p = parent
        while not p.exists() and p != self._root:
            parts_to_create.append(p)
            p = p.parent
        parent.mkdir(parents=True, exist_ok=True)
        # Установить mode 0o777 на новосозданные директории
        for p in parts_to_create:
            try:
                p.chmod(0o777)
            except OSError:
                pass
        sha = hashlib.sha256()
        size = 0
        async with aiofiles.open(path, "wb") as f:
            async for chunk in data:
                sha.update(chunk)
                size += len(chunk)
                await f.write(chunk)
        return size, sha.hexdigest()

    async def get(self, key: str) -> AsyncIterator[bytes]:
        path = self._resolve(key)
        async with aiofiles.open(path, "rb") as f:
            while True:
                chunk = await f.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    async def open_path(self, key: str) -> Path:
        return self._resolve(key)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)
