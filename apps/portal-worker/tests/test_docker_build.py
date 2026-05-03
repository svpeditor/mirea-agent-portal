"""builder/docker_build.py -- real docker build on a small image."""
import contextlib
import shutil
from pathlib import Path

import pytest

if shutil.which("docker") is None:
    pytest.skip("docker not available", allow_module_level=True)


@pytest.fixture()
def trivial_build_context(tmp_path: Path) -> Path:
    """Minimal context: Dockerfile + one agent.py file."""
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    (ctx / "Dockerfile.portal").write_text("""\
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /agent
COPY agent.py /agent/agent.py
RUN useradd --create-home --shell /bin/bash agent && chown -R agent:agent /agent
USER agent
ENTRYPOINT ["python", "agent.py"]
""")
    (ctx / "agent.py").write_text("print('hi')\n")
    return ctx


def test_build_succeeds(trivial_build_context: Path) -> None:
    """Pulling python:3.12-slim + small build should succeed."""
    from portal_worker.builder.docker_build import build_image

    tag = "portal-test/build-success:t1"
    try:
        log = build_image(
            context_dir=trivial_build_context,
            dockerfile_name="Dockerfile.portal",
            tag=tag, timeout_seconds=600,
            memory_limit_bytes=2 * 1024**3,
        )
        assert isinstance(log, str)
        assert "Successfully" in log or "writing image" in log
    finally:
        import docker
        with contextlib.suppress(Exception):
            docker.from_env().images.remove(tag, force=True)


def test_build_fails_on_bad_dockerfile(tmp_path: Path) -> None:
    from portal_worker.builder.docker_build import build_image
    from portal_worker.core.exceptions import BuildError

    ctx = tmp_path / "bad"
    ctx.mkdir()
    (ctx / "Dockerfile.portal").write_text("FROM python:3.12-slim\nRUN exit 1\n")

    with pytest.raises(BuildError) as exc:
        build_image(
            context_dir=ctx, dockerfile_name="Dockerfile.portal",
            tag="portal-test/badbuild:t1", timeout_seconds=120,
            memory_limit_bytes=2 * 1024**3,
        )
    assert exc.value.code == "docker_error"


def test_image_size_returned_after_success(trivial_build_context: Path) -> None:
    from portal_worker.builder.docker_build import build_image, image_size_bytes

    tag = "portal-test/size:t1"
    try:
        build_image(
            context_dir=trivial_build_context, dockerfile_name="Dockerfile.portal",
            tag=tag, timeout_seconds=600, memory_limit_bytes=2 * 1024**3,
        )
        size = image_size_bytes(tag)
        assert size > 0
    finally:
        import docker
        with contextlib.suppress(Exception):
            docker.from_env().images.remove(tag, force=True)
