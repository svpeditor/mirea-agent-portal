"""Создание bare-clone из локальной директории для тестов."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def make_bare_repo_from_dir(src: Path, dest_root: Path, name: str = "bare") -> Path:
    """Создаёт bare-репо c одним коммитом из содержимого src."""
    work = dest_root / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    subprocess.run(["cp", "-R", str(src) + "/.", str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-m",
            "init",
        ],
        check=True,
        capture_output=True,
    )

    bare = dest_root / f"{name}.git"
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)], check=True, capture_output=True
    )
    return bare


def make_oversize_bare_repo(dest_root: Path, size_mb: int = 60) -> Path:
    """Bare-репо с одним блобом размером size_mb."""  # noqa: RUF002
    work = dest_root / "big-work"
    work.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    blob = work / "big.bin"
    blob.write_bytes(b"\0" * (size_mb * 1024 * 1024))
    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-m",
            "big",
        ],
        check=True,
        capture_output=True,
    )
    bare = dest_root / "big.git"
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)], check=True, capture_output=True
    )
    return bare
