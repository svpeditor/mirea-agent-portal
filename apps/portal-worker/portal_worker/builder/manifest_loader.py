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
    allowed_llm_models: list[str],
) -> Manifest:
    """Парсит manifest.yaml + проверяет id_mismatch, base_image_whitelist и runtime.llm."""
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

    base_image = manifest.runtime.docker.base_image.strip()
    if base_image not in allowed_base_images:
        raise BuildError(
            "base_image_not_allowed",
            f"base_image={manifest.runtime.docker.base_image!r} "
            f"не входит в whitelist {allowed_base_images}",
        )

    if manifest.runtime.llm is not None:
        # Провайдер уже валидируется Pydantic (Literal["openrouter"]),
        # но защищаем на случай расширения схемы до Union.
        if manifest.runtime.llm.provider != "openrouter":
            raise BuildError(
                "provider_not_supported",
                f"runtime.llm.provider={manifest.runtime.llm.provider!r}; "
                f"only 'openrouter' is supported on this version of portal",
            )
        if not manifest.runtime.llm.models:
            raise BuildError(
                "llm_models_empty",
                "runtime.llm.models must be a non-empty list",
            )
        for model in manifest.runtime.llm.models:
            if model not in allowed_llm_models:
                raise BuildError(
                    "model_not_allowed",
                    f"model {model!r} is not in global whitelist {allowed_llm_models}",
                )

    return manifest
