"""Клонирование репозитория агента с лимитами."""  # noqa: RUF002
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from portal_worker.core.exceptions import BuildError

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _du_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total


def clone_at_sha(
    git_url: str,
    *,
    git_ref: str,
    target_dir: Path,
    max_repo_size_bytes: int,
    clone_timeout: int,
) -> str:
    """Клонирует git_url в target_dir, выполняет checkout git_ref, возвращает 40-char SHA.

    Raises:
        BuildError(code='clone_failed', log=...) — при ошибке git или таймауте.
        BuildError(code='repo_too_large', log=...) — если размер клона > max_repo_size_bytes.
    """
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    is_sha = bool(_FULL_SHA.match(git_ref))
    try:
        if is_sha:
            subprocess.run(
                ["git", "clone", git_url, str(target_dir)],
                check=True,
                timeout=clone_timeout,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(target_dir), "checkout", git_ref],
                check=True,
                timeout=10,
                capture_output=True,
            )
        else:
            subprocess.run(
                ["git", "clone", "--depth=1", "--branch", git_ref, git_url, str(target_dir)],
                check=True,
                timeout=clone_timeout,
                capture_output=True,
            )
    except subprocess.TimeoutExpired as exc:
        raise BuildError("clone_failed", f"timeout after {exc.timeout}s") from exc
    except subprocess.CalledProcessError as exc:
        log = (exc.stderr or b"").decode(errors="replace")
        raise BuildError("clone_failed", log) from exc

    size = _du_bytes(target_dir)
    if size > max_repo_size_bytes:
        raise BuildError(
            "repo_too_large",
            f"repo size {size} > limit {max_repo_size_bytes}",
        )

    return subprocess.run(
        ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        timeout=5,
    ).stdout.decode().strip()
