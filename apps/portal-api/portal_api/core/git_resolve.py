"""Лёгкая резолюция git-ref в SHA без полного клона.

Используется в admin endpoints для ранней валидации git_url + git_ref
до постановки билда в очередь.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

from portal_api.core.exceptions import InvalidGitRefError, InvalidGitUrlError

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_LS_REMOTE_TIMEOUT_SECONDS = 15


def _is_supported_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"https", "file"} and bool(parsed.path)


async def resolve_git_ref(git_url: str, git_ref: str) -> str:
    """Возвращает 40-символьный SHA для пары (url, ref).

    Raises:
        InvalidGitUrlError: URL не https/file или git ls-remote вернул ошибку/timeout.
        InvalidGitRefError: ref не найден среди heads/tags и не является валидным SHA.
    """
    if not _is_supported_url(git_url):
        raise InvalidGitUrlError()

    proc = await asyncio.create_subprocess_exec(
        "git",
        "ls-remote",
        "--heads",
        "--tags",
        git_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_LS_REMOTE_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        proc.kill()
        raise InvalidGitUrlError() from exc

    if proc.returncode != 0:
        raise InvalidGitUrlError()

    refs: dict[str, str] = {}
    shas: set[str] = set()
    for line in stdout.decode().splitlines():
        if not line.strip():
            continue
        sha, name = line.split("\t", 1)
        refs[name] = sha
        # heads/main, tags/v1, tags/v1^{} — также раскрываем короткое имя
        short = name.split("/", 2)[-1]
        refs[short] = sha
        shas.add(sha)

    # Прямое совпадение SHA
    if _FULL_SHA.match(git_ref) and git_ref in shas:
        return git_ref

    if git_ref in refs:
        return refs[git_ref]

    raise InvalidGitRefError()
