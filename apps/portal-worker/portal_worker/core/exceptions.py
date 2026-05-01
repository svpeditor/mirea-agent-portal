"""Исключения worker-процесса."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BuildError(Exception):
    """Ошибка сборки Docker-образа агента."""

    code: str
    log: str = field(default="")

    def __str__(self) -> str:  # pragma: no cover
        return f"BuildError({self.code}): {self.log[:200]}"
