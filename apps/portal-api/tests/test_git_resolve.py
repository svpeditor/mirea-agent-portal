"""Резолюция git-ref в SHA через ls-remote."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def local_bare_repo(tmp_path: Path) -> Path:
    """Создаёт пустой bare-репо с одним коммитом и тегом."""
    work = tmp_path / "work"
    work.mkdir()
    bare = tmp_path / "bare.git"

    subprocess.run(["git", "init", "-b", "main", str(work)], check=True)
    (work / "README.md").write_text("hi")
    subprocess.run(["git", "-C", str(work), "add", "README.md"], check=True)
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
    )
    subprocess.run(["git", "-C", str(work), "tag", "v1"], check=True)
    subprocess.run(["git", "clone", "--bare", str(work), str(bare)], check=True)
    return bare


async def test_resolves_main(local_bare_repo: Path) -> None:
    from portal_api.core.git_resolve import resolve_git_ref

    sha = await resolve_git_ref(f"file://{local_bare_repo}", "main")
    assert len(sha) == 40
    assert all(c in "0123456789abcdef" for c in sha)


async def test_resolves_tag(local_bare_repo: Path) -> None:
    from portal_api.core.git_resolve import resolve_git_ref

    sha = await resolve_git_ref(f"file://{local_bare_repo}", "v1")
    assert len(sha) == 40


async def test_invalid_url_raises(tmp_path: Path) -> None:
    from portal_api.core.exceptions import InvalidGitUrlError
    from portal_api.core.git_resolve import resolve_git_ref

    with pytest.raises(InvalidGitUrlError):
        await resolve_git_ref(f"file://{tmp_path / 'doesnotexist.git'}", "main")


async def test_invalid_ref_raises(local_bare_repo: Path) -> None:
    from portal_api.core.exceptions import InvalidGitRefError
    from portal_api.core.git_resolve import resolve_git_ref

    with pytest.raises(InvalidGitRefError):
        await resolve_git_ref(f"file://{local_bare_repo}", "no-such-branch-xyz")


async def test_passes_full_sha_through(local_bare_repo: Path) -> None:
    """Если ref уже выглядит как 40-символьный SHA, проверяем что он
    есть в репо через ls-remote (или просто доверяем — в зависимости
    от реализации). Здесь проверяем «корректный SHA → возвращается как есть»."""
    from portal_api.core.git_resolve import resolve_git_ref

    sha_main = await resolve_git_ref(f"file://{local_bare_repo}", "main")
    sha_again = await resolve_git_ref(f"file://{local_bare_repo}", sha_main)
    assert sha_again == sha_main
