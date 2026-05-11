"""Зарегистрировать агента из локального источника (ZIP или wizard-template).

Подход: создаём bare-like локальный git-репо в file_store_local_root и
возвращаем `file:///<path>` URL — дальше всё идёт по обычному пайплайну
(create_agent → resolve_git_ref → manifest fetch → enqueue build).

Worker и api шарят /var/portal-files, поэтому `git clone file://...`
работает из обоих контейнеров.
"""
from __future__ import annotations

import asyncio
import io
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path
from typing import Final


_AGENT_SOURCES_DIR: Final = "agent-sources"
_REQUIRED_FILES: Final = ("manifest.yaml",)


class AgentUploadError(Exception):
    """ZIP/template невалидный (нет manifest, опасные пути и т.д.)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _safe_member(name: str) -> bool:
    """Защита от zip-slip: нельзя ../ и абсолютные пути."""
    if name.startswith("/"):
        return False
    parts = Path(name).parts
    return ".." not in parts


def _detect_top_dir(names: list[str]) -> str | None:
    """Если все файлы внутри одной top-level папки — вернуть её имя.

    Пример: ZIP с `my-agent/manifest.yaml`, `my-agent/agent.py` → 'my-agent'.
    Нужно чтобы автоматически развернуть содержимое.
    """
    tops = set()
    for n in names:
        if not n or n.endswith("/"):
            continue
        first = n.split("/", 1)[0]
        tops.add(first)
        if len(tops) > 1:
            return None
    return next(iter(tops)) if len(tops) == 1 else None


def _extract_zip(zip_bytes: bytes, target: Path) -> None:
    """Безопасное извлечение, авто-распаковка одного top-dir'а."""
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        for n in names:
            if not _safe_member(n):
                raise AgentUploadError("UNSAFE_PATH", f"опасный путь в zip: {n!r}")

        top = _detect_top_dir(names)
        for info in zf.infolist():
            n = info.filename
            if top and n.startswith(top + "/"):
                n = n[len(top) + 1:]
            if not n:
                continue
            dest = target / n
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _git_init_commit(repo_dir: Path) -> None:
    """git init + add + commit. Без user.email — задаём локально."""
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin:/usr/local/bin"}
    for cmd in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "config", "user.email", "portal@mirea.local"],
        ["git", "config", "user.name", "portal"],
        ["git", "add", "."],
        ["git", "commit", "-q", "-m", "initial upload"],
    ):
        subprocess.run(cmd, cwd=str(repo_dir), env=env, check=True, capture_output=True)
    # Worker крутится под uid 1000, api — root. После git init файлы созданы
    # root'ом и worker не может прочитать (`dubious ownership`).
    # Chown'им всё дерево на uid 1000 (worker), gid тот же.
    _chown_to_worker(repo_dir)


def _chown_to_worker(repo_dir: Path) -> None:
    """chown -R 1000:1000 на всё дерево, чтобы worker мог git clone."""
    import os
    WORKER_UID = 1000
    WORKER_GID = 1000
    for p in [repo_dir, *repo_dir.rglob("*")]:
        try:
            os.chown(p, WORKER_UID, WORKER_GID)
        except (PermissionError, OSError):
            try:
                p.chmod(0o777 if p.is_dir() else 0o666)
            except OSError:
                pass


def _validate_source(root: Path) -> None:
    for f in _REQUIRED_FILES:
        if not (root / f).exists():
            raise AgentUploadError(
                "MISSING_MANIFEST",
                f"в архиве нет {f} (должен быть в корне или в одной top-папке).",
            )


def stage_zip_as_local_repo(zip_bytes: bytes, file_store_root: Path) -> tuple[str, str]:
    """Извлечь zip, превратить в git-репо, вернуть (git_url, git_ref).

    Returns:
        (`file:///абс/путь/к/репо`, `main`)
    """
    return _stage_local_repo(file_store_root, lambda dest: _extract_zip(zip_bytes, dest))


def stage_template_as_local_repo(
    files: dict[str, str | bytes],
    file_store_root: Path,
) -> tuple[str, str]:
    """Из dict {relative_path: content} собрать локальный git-репо."""
    def _write(dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        for rel, content in files.items():
            p = dest / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, str):
                p.write_text(content, encoding="utf-8")
            else:
                p.write_bytes(content)

    return _stage_local_repo(file_store_root, _write)


def _stage_local_repo(file_store_root: Path, writer) -> tuple[str, str]:
    """Общий код: создать dir, наполнить через `writer`, валидировать, git init."""
    uid = uuid.uuid4().hex[:12]
    repo_dir = file_store_root / _AGENT_SOURCES_DIR / uid
    try:
        writer(repo_dir)
        _validate_source(repo_dir)
        _git_init_commit(repo_dir)
    except AgentUploadError:
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise AgentUploadError("STAGE_FAILED", str(e)) from e

    return f"file://{repo_dir}", "main"


async def stage_zip_as_local_repo_async(
    zip_bytes: bytes, file_store_root: Path,
) -> tuple[str, str]:
    return await asyncio.to_thread(stage_zip_as_local_repo, zip_bytes, file_store_root)


async def stage_template_as_local_repo_async(
    files: dict[str, str | bytes], file_store_root: Path,
) -> tuple[str, str]:
    return await asyncio.to_thread(stage_template_as_local_repo, files, file_store_root)
