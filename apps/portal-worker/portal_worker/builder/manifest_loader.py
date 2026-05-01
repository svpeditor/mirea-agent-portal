"""Парсинг + валидация manifest.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml
from portal_sdk.manifest import Manifest
from pydantic import ValidationError

from portal_worker.core.exceptions import BuildError


def load_and_validate_manifest(
    *,
    repo_dir: Path,
    agent_slug: str,
    allowed_base_images: list[str],
) -> Manifest:
    manifest_path = repo_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise BuildError(
            "manifest_not_found",
            f"manifest.yaml не найден в корне репозитория ({repo_dir})",
        )

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BuildError("manifest_invalid", f"YAML parse: {exc}") from exc

    try:
        manifest = Manifest.model_validate(raw)
    except ValidationError as exc:
        raise BuildError("manifest_invalid", str(exc)) from exc

    if manifest.id != agent_slug:
        raise BuildError(
            "manifest_invalid",
            f"id_mismatch: manifest.id={manifest.id!r} != agent.slug={agent_slug!r}",
        )

    if manifest.runtime.docker.base_image not in allowed_base_images:
        raise BuildError(
            "base_image_not_allowed",
            f"base_image={manifest.runtime.docker.base_image!r} "
            f"не входит в whitelist {allowed_base_images}",
        )

    return manifest
