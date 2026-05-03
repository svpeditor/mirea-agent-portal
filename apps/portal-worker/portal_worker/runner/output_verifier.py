"""Верификация и сканирование output_dir после exit агента."""
from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


class OutputMissingError(Exception):
    """Объявленный manifest.outputs[*].filename не найден в output_dir."""


@dataclass
class ScannedFile:
    relative_path: str  # под output_dir
    absolute_path: Path
    size_bytes: int
    sha256: str


def verify_outputs(output_dir: Path, *, declared_filenames: Iterable[str]) -> None:
    for fname in declared_filenames:
        if not (output_dir / fname).is_file():
            raise OutputMissingError(
                f"output file not found: {fname!r} in {output_dir}"
            )


def scan_output_dir(output_dir: Path) -> list[ScannedFile]:
    """Recursively просканировать output_dir, посчитать sha256/size для каждого файла."""
    out: list[ScannedFile] = []
    for p in output_dir.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        rel = str(p.relative_to(output_dir))
        sha = hashlib.sha256()
        size = 0
        with p.open("rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                sha.update(chunk)
                size += len(chunk)
        out.append(ScannedFile(
            relative_path=rel, absolute_path=p,
            size_bytes=size, sha256=sha.hexdigest(),
        ))
    return out
