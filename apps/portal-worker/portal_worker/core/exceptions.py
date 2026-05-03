"""Исключения уровня worker."""
from __future__ import annotations


class BuildError(Exception):
    """Любая ошибка билда: содержит код для agent_versions.build_error."""

    def __init__(self, code: str, log: str = "") -> None:
        super().__init__(f"{code}: {log[:200]}")
        self.code = code
        self.log = log
