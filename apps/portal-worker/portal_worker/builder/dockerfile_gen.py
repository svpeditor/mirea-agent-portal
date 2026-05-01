"""Генерация Dockerfile.portal из manifest.

Студенческий Dockerfile (если есть в репо) не используется — портал
генерирует свой, чтобы гарантировать unified runtime: SDK injection,
non-root user, exec-form entrypoint.
"""
from __future__ import annotations

import json

from portal_sdk.manifest import Manifest

from portal_worker.core.exceptions import BuildError

_TEMPLATE = """FROM {base_image}

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /agent

# SDK устанавливается первым — отдельный layer для кеширования.
COPY .portal-sdk /sdk
RUN pip install --no-cache-dir /sdk

# Код агента (до setup, чтобы setup мог читать requirements.txt и т.п.)
COPY . /agent
RUN rm -rf /agent/.portal-sdk /agent/Dockerfile.portal

# Setup студента из manifest.runtime.docker.setup
{setup_block}

# Non-root
RUN useradd --create-home --shell /bin/bash agent && chown -R agent:agent /agent
USER agent

ENTRYPOINT {entrypoint_json}
"""


def generate_dockerfile(manifest: Manifest) -> str:
    base_image = manifest.runtime.docker.base_image
    if "\n" in base_image or "\r" in base_image:
        raise BuildError(
            "manifest_invalid",
            f"base_image contains newline: {base_image!r}",
        )
    setup_lines = manifest.runtime.docker.setup or []
    for line in setup_lines:
        if "\n" in line or "\r" in line:
            raise BuildError(
                "manifest_invalid",
                f"setup line contains newline: {line!r}",
            )
    setup_block = "\n".join(f"RUN {line}" for line in setup_lines) or "# (no setup)"
    entrypoint_json = json.dumps(list(manifest.runtime.docker.entrypoint), ensure_ascii=False)
    # str.format() substituted values are not re-parsed for format fields, so
    # user setup lines like 'bash -c "rm /tmp/{a,b}"' are safe to pass as-is.
    return _TEMPLATE.format(
        base_image=base_image,
        setup_block=setup_block,
        entrypoint_json=entrypoint_json,
    )
