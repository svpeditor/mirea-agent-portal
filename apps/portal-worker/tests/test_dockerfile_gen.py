"""builder/dockerfile_gen.py — генерация Dockerfile из manifest."""
from portal_sdk.manifest import Manifest


def _make_manifest(setup: list[str] | None = None,
                   entrypoint: list[str] | None = None,
                   base_image: str = "python:3.12-slim") -> Manifest:
    return Manifest.model_validate({
        "id": "x", "name": "X", "version": "0.1.0", "category": "научная-работа",
        "short_description": "d",
        "inputs": {}, "files": {}, "outputs": [
            {"id": "o", "type": "any", "label": "o", "filename": "o.txt"},
        ],
        "runtime": {
            "docker": {
                "base_image": base_image,
                "setup": setup or [],
                "entrypoint": entrypoint or ["python", "agent.py"],
            },
            "llm": {"provider": "openrouter", "models": []},
            "limits": {"max_runtime_minutes": 1, "max_memory_mb": 128, "max_cpu_cores": 1},
        },
    })


def test_basic_dockerfile_contains_from() -> None:
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    df = generate_dockerfile(_make_manifest())
    assert df.startswith("FROM python:3.12-slim")
    assert "WORKDIR /agent" in df


def test_setup_lines_become_run() -> None:
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    df = generate_dockerfile(_make_manifest(setup=[
        "pip install requests", "apt-get update", "apt-get install -y curl",
    ]))
    assert "RUN pip install requests" in df
    assert "RUN apt-get update" in df
    assert "RUN apt-get install -y curl" in df


def test_entrypoint_is_exec_form() -> None:
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    df = generate_dockerfile(_make_manifest(entrypoint=["python", "main.py", "--mode=run"]))
    assert 'ENTRYPOINT ["python", "main.py", "--mode=run"]' in df


def test_user_agent_is_set() -> None:
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    df = generate_dockerfile(_make_manifest())
    assert "USER agent" in df
    assert "useradd" in df


def test_sdk_install_layer_is_first() -> None:
    """SDK устанавливается до setup — для кеша слоёв."""
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    df = generate_dockerfile(_make_manifest(setup=["pip install foo"]))
    sdk_pos = df.index("pip install --no-cache-dir /sdk")
    user_setup_pos = df.index("pip install foo")
    assert sdk_pos < user_setup_pos


def test_all_three_python_versions_supported() -> None:
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    for img in ["python:3.11-slim", "python:3.12-slim", "python:3.13-slim"]:
        df = generate_dockerfile(_make_manifest(base_image=img))
        assert df.startswith(f"FROM {img}")


def test_newline_in_base_image_raises() -> None:
    import pytest as _pytest

    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    from portal_worker.core.exceptions import BuildError
    with _pytest.raises(BuildError) as exc:
        generate_dockerfile(_make_manifest(base_image="python:3.12-slim\nRUN evil"))
    assert exc.value.code == "manifest_invalid"


def test_newline_in_setup_raises() -> None:
    import pytest as _pytest

    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    from portal_worker.core.exceptions import BuildError
    with _pytest.raises(BuildError) as exc:
        generate_dockerfile(_make_manifest(setup=["pip install foo\nRUN evil"]))
    assert exc.value.code == "manifest_invalid"


def test_brace_in_setup_does_not_crash() -> None:
    from portal_worker.builder.dockerfile_gen import generate_dockerfile
    df = generate_dockerfile(_make_manifest(setup=['bash -c "rm /tmp/{a,b}"']))
    assert 'RUN bash -c "rm /tmp/{a,b}"' in df
