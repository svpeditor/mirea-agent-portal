"""Запуск Docker-контейнера агента + стрим JSONL stdout."""
from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import docker
import structlog

from portal_worker.runner.jsonl_parser import parse_jsonl_stream


class RunTimeout(Exception):  # noqa: N818
    """Контейнер не уложился в timeout."""


class RunCancelled(Exception):  # noqa: N818
    """cancel_check вернул True — контейнер был остановлен пользователем."""


def run_agent_container(
    *,
    image_tag: str,
    input_dir: Path,
    output_dir: Path,
    params_path: Path,
    memory_mb: int,
    cpu_cores: float,
    timeout_seconds: int,
    cancel_check: Callable[[], bool],
    on_event: Callable[[dict[str, Any]], None],
    labels: dict[str, str],
) -> int:
    """Запустить контейнер, парсить stdout, ёмитить events. Возвращает exit_code.

    raises:
        RunTimeout — если контейнер не завершился за timeout_seconds.
        RunCancelled — если cancel_check вернул True во время выполнения.
    """
    structlog.get_logger().bind(image=image_tag)  # reserved for future log calls
    client = docker.from_env()
    container = client.containers.run(
        image=image_tag,
        detach=True,
        network_mode="none",
        read_only=True,
        tmpfs={"/tmp": "size=64m,mode=1777"},  # noqa: S108
        mem_limit=f"{memory_mb}m",
        nano_cpus=int(cpu_cores * 1e9),
        volumes={
            str(input_dir):  {"bind": "/var/agent/input",      "mode": "ro"},
            str(output_dir): {"bind": "/var/agent/output",     "mode": "rw"},
            str(params_path):{"bind": "/var/agent/params.json","mode": "ro"},
        },
        environment={
            "PARAMS_FILE": "/var/agent/params.json",
            "INPUT_DIR":   "/var/agent/input",
            "OUTPUT_DIR":  "/var/agent/output",
        },
        labels=labels,
    )

    start_ts = time.monotonic()
    cancelled = False
    timed_out = False
    stream_done = False  # set by main thread when stdout stream is fully drained

    def _watcher() -> None:
        nonlocal cancelled, timed_out
        while True:
            time.sleep(1.0)
            if stream_done:           # stream drained = container effectively done
                return
            try:
                container.reload()
                if container.status in ("exited", "dead"):
                    return
            except docker.errors.NotFound:
                return
            if cancel_check():
                cancelled = True
                with contextlib.suppress(Exception):
                    container.stop(timeout=10)
                return
            if time.monotonic() - start_ts > timeout_seconds:
                timed_out = True
                with contextlib.suppress(Exception):
                    container.stop(timeout=10)
                return

    watcher = threading.Thread(target=_watcher, daemon=True)
    watcher.start()

    try:
        # Stream stdout (line-buffered byte chunks)
        for event in parse_jsonl_stream(
            container.logs(stream=True, follow=True, stdout=True, stderr=False),
            flush_on_eof=True,
        ):
            on_event(event)
        stream_done = True            # signal watcher to back off before container.wait
        # Дождаться exit
        result = container.wait(timeout=timeout_seconds + 30)
        exit_code = int(result.get("StatusCode", -1))
    finally:
        with contextlib.suppress(Exception):
            container.remove(force=True)
        watcher.join(timeout=2)

    if cancelled:
        raise RunCancelled()
    if timed_out:
        raise RunTimeout(f"timeout after {timeout_seconds}s")
    return exit_code
