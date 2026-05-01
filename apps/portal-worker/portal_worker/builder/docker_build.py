"""Сборка Docker-образа агента через Docker Engine SDK."""
from __future__ import annotations

import concurrent.futures
import contextlib
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError
from docker.errors import BuildError as DockerBuildError

from portal_worker.core.exceptions import BuildError


def _format_log_lines(stream: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for chunk in stream:
        if "stream" in chunk:
            out.append(chunk["stream"].rstrip())
        elif "errorDetail" in chunk:
            out.append("ERROR: " + chunk["errorDetail"].get("message", str(chunk)))
        elif "error" in chunk:
            out.append("ERROR: " + str(chunk["error"]))
    return "\n".join(out)


def _do_build(
    context_dir: Path,
    dockerfile_name: str,
    tag: str,
    memory_limit_bytes: int,
) -> tuple[Any, list[dict[str, Any]]]:
    client = docker.from_env()
    image, raw_stream = client.images.build(
        path=str(context_dir),
        dockerfile=dockerfile_name,
        tag=tag,
        rm=True,
        forcerm=True,
        pull=True,
        nocache=False,
        container_limits={"memory": memory_limit_bytes},
        labels={"portal-build": tag},
    )
    return image, list(raw_stream)


def build_image(
    *,
    context_dir: Path,
    dockerfile_name: str,
    tag: str,
    timeout_seconds: int,
    memory_limit_bytes: int,
) -> str:
    """Run docker build with a timeout. Returns stdout log string.

    raises:
        BuildError(code='build_timeout') -- timeout_seconds exceeded.
        BuildError(code='docker_error') -- any docker engine error.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(
            _do_build, context_dir, dockerfile_name, tag, memory_limit_bytes,
        )
        try:
            _, stream = future.result(timeout=timeout_seconds)
        except TimeoutError as exc:
            # Best-effort kill all intermediate containers by label
            with contextlib.suppress(Exception):
                client = docker.from_env()
                for c in client.containers.list(filters={"label": f"portal-build={tag}"}):
                    c.kill()
            raise BuildError("build_timeout", f"timeout after {timeout_seconds}s") from exc
        except DockerBuildError as exc:
            log = _format_log_lines(list(exc.build_log))
            raise BuildError("docker_error", log) from exc
        except APIError as exc:
            raise BuildError("docker_error", str(exc)) from exc

    return _format_log_lines(stream)


def image_size_bytes(tag: str) -> int:
    return int(docker.from_env().images.get(tag).attrs["Size"])


def remove_image(tag: str) -> None:
    with contextlib.suppress(Exception):
        docker.from_env().images.remove(tag, force=True)
