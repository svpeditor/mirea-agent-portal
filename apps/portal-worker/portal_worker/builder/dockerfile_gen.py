"""Генерация Dockerfile.portal из manifest.

Студенческий Dockerfile (если есть в репо) не используется — портал
генерирует свой, чтобы гарантировать unified runtime: SDK injection,
non-root user, exec-form entrypoint.
"""
from __future__ import annotations

import json

from portal_sdk.manifest import Manifest

_TEMPLATE = """FROM {base_image}

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /agent

# SDK устанавливается первым — отдельный layer для кеширования.
COPY .portal-sdk /sdk
RUN pip install --no-cache-dir /sdk

# Setup студента из manifest.runtime.docker.setup
{setup_block}

# Код агента
COPY . /agent
RUN rm -rf /agent/.portal-sdk /agent/Dockerfile.portal

# Non-root
RUN useradd --create-home --shell /bin/bash agent && chown -R agent:agent /agent
USER agent

ENTRYPOINT {entrypoint_json}
"""


def generate_dockerfile(manifest: Manifest) -> str:
    setup_lines = manifest.runtime.docker.setup or []
    setup_block = "\n".join(f"RUN {line}" for line in setup_lines) or "# (no setup)"
    entrypoint_json = json.dumps(list(manifest.runtime.docker.entrypoint), ensure_ascii=False)
    return _TEMPLATE.format(
        base_image=manifest.runtime.docker.base_image,
        setup_block=setup_block,
        entrypoint_json=entrypoint_json,
    )
