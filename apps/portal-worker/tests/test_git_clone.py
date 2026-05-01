"""builder/git_clone.py — клонирование с лимитами."""  # noqa: RUF002
from pathlib import Path

import pytest

from tests.fixtures.git_repo import make_bare_repo_from_dir, make_oversize_bare_repo


@pytest.fixture()
def echo_bare(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[3] / "agents" / "echo"
    return make_bare_repo_from_dir(src, tmp_path)


def test_clone_resolves_sha(echo_bare: Path, tmp_path: Path) -> None:
    from portal_worker.builder.git_clone import clone_at_sha

    target = tmp_path / "out"
    sha = clone_at_sha(
        f"file://{echo_bare}",
        git_ref="main",
        target_dir=target,
        max_repo_size_bytes=50 * 1024 * 1024,
        clone_timeout=60,
    )
    assert len(sha) == 40
    assert (target / "manifest.yaml").exists()


def test_clone_invalid_url_raises(tmp_path: Path) -> None:
    from portal_worker.builder.git_clone import clone_at_sha
    from portal_worker.core.exceptions import BuildError

    with pytest.raises(BuildError) as exc:
        clone_at_sha(
            f"file://{tmp_path / 'nope.git'}",
            git_ref="main",
            target_dir=tmp_path / "out",
            max_repo_size_bytes=50 * 1024 * 1024,
            clone_timeout=10,
        )
    assert exc.value.code == "clone_failed"


def test_clone_invalid_ref_raises(echo_bare: Path, tmp_path: Path) -> None:
    from portal_worker.builder.git_clone import clone_at_sha
    from portal_worker.core.exceptions import BuildError

    with pytest.raises(BuildError) as exc:
        clone_at_sha(
            f"file://{echo_bare}",
            git_ref="no-such-ref-xyz",
            target_dir=tmp_path / "out",
            max_repo_size_bytes=50 * 1024 * 1024,
            clone_timeout=60,
        )
    assert exc.value.code == "clone_failed"


def test_clone_repo_too_large(tmp_path: Path) -> None:
    from portal_worker.builder.git_clone import clone_at_sha
    from portal_worker.core.exceptions import BuildError

    big = make_oversize_bare_repo(tmp_path, size_mb=60)
    with pytest.raises(BuildError) as exc:
        clone_at_sha(
            f"file://{big}",
            git_ref="main",
            target_dir=tmp_path / "out",
            max_repo_size_bytes=50 * 1024 * 1024,
            clone_timeout=120,
        )
    assert exc.value.code == "repo_too_large"


def test_clone_returns_directory_with_files(echo_bare: Path, tmp_path: Path) -> None:
    from portal_worker.builder.git_clone import clone_at_sha

    target = tmp_path / "out"
    clone_at_sha(
        f"file://{echo_bare}",
        git_ref="main",
        target_dir=target,
        max_repo_size_bytes=50 * 1024 * 1024,
        clone_timeout=60,
    )
    assert (target / "agent.py").exists()
    assert (target / "Dockerfile").exists()
