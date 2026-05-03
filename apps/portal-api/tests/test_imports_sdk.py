"""Smoke: portal_sdk виден из portal_api как path-dep."""


def test_portal_sdk_manifest_importable() -> None:
    from portal_sdk.manifest import CategoryStrict, Manifest

    assert hasattr(Manifest, "model_validate")
    assert {c.value for c in CategoryStrict} == {
        "научная-работа",
        "учебная",
        "организационная",
    }


def test_rq_redis_importable() -> None:
    from redis import Redis  # noqa: F401
    from rq import Queue  # noqa: F401


def test_gitpython_importable() -> None:
    from git import Repo  # noqa: F401
