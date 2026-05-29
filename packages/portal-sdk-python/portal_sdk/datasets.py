"""Клиент общей базы данных портала для агентов.

Агент пишет и читает записи общей базы через sandbox-эндпоинты portal-api.
Доступ (read/write) объявляется в manifest.yaml -> runtime.datasets. Один агент
наполняет базу (задачи/решения в LaTeX, классификаторы), другие читают.

Пример::

    from portal_sdk import Agent

    a = Agent()
    ds = a.dataset("math-tasks")
    ds.put("task-001", content=r"\\section{Задача}...", content_format="latex")
    rec = ds.get("task-001")          # {'key':..., 'content':..., ...} | None
    page = ds.list(prefix="task-")    # {'items':[...], 'total':N, ...}
"""
# ruff: noqa: RUF001
from __future__ import annotations

import os
from typing import Any

import httpx

_DEFAULT_TIMEOUT = 60.0


class DatasetError(RuntimeError):
    """Ошибка обращения к общей базе (не считая 404 в get/delete)."""


def _resolve_base_url() -> str:
    base = os.environ.get("PORTAL_API_BASE_URL")
    if not base:
        # Fallback: исторически агенты ходили в sandbox через OPENROUTER_BASE_URL.
        proxy = os.environ.get("OPENROUTER_BASE_URL", "")
        b = proxy.rstrip("/")
        if b.endswith("/llm/v1"):
            b = b[: -len("/llm/v1")]
        base = b
    if not base:
        raise DatasetError(
            "Не задан PORTAL_API_BASE_URL — общая база доступна только агенту, "
            "запущенному порталом (или через portal-sdk-run-local)."
        )
    return base.rstrip("/")


def _resolve_token() -> str:
    token = os.environ.get("PORTAL_AGENT_TOKEN") or os.environ.get("OPENROUTER_API_KEY")
    if not token:
        raise DatasetError(
            "Не задан PORTAL_AGENT_TOKEN — нет ephemeral-токена для доступа к базе."
        )
    return token


class DatasetClient:
    """Доступ к одному датасету (по slug). Создаётся через Agent.dataset(slug)."""

    def __init__(
        self,
        slug: str,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._slug = slug
        self._base = (base_url or _resolve_base_url()).rstrip("/")
        self._token = token or _resolve_token()
        self._timeout = timeout

    @property
    def _root(self) -> str:
        return f"{self._base}/api/sandbox/datasets/{self._slug}"

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def put(
        self,
        key: str,
        *,
        value: dict[str, Any] | None = None,
        content: str | None = None,
        content_format: str = "json",
    ) -> dict[str, Any]:
        """Записать/обновить запись по ключу. Нужен write/readwrite-грант."""
        if value is None and content is None:
            raise ValueError("put(): нужно передать value и/или content.")
        body: dict[str, Any] = {"key": key, "content_format": content_format}
        if value is not None:
            body["value"] = value
        if content is not None:
            body["content"] = content
        with httpx.Client(timeout=self._timeout) as c:
            r = c.put(f"{self._root}/record", json=body, headers=self._headers)
        self._raise_for_status(r)
        return r.json()

    def get(self, key: str) -> dict[str, Any] | None:
        """Прочитать запись. Возвращает None если ключа нет. Нужен read-грант."""
        with httpx.Client(timeout=self._timeout) as c:
            r = c.get(
                f"{self._root}/record", params={"key": key}, headers=self._headers
            )
        if r.status_code == 404:
            return None
        self._raise_for_status(r)
        return r.json()

    def list(
        self, *, prefix: str | None = None, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """Список записей: {'items': [...], 'total': N, 'limit':.., 'offset':..}."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if prefix is not None:
            params["prefix"] = prefix
        with httpx.Client(timeout=self._timeout) as c:
            r = c.get(f"{self._root}/records", params=params, headers=self._headers)
        self._raise_for_status(r)
        return r.json()

    def delete(self, key: str) -> bool:
        """Удалить запись. True если удалена, False если ключа не было."""
        with httpx.Client(timeout=self._timeout) as c:
            r = c.request(
                "DELETE", f"{self._root}/record",
                params={"key": key}, headers=self._headers,
            )
        if r.status_code == 404:
            return False
        self._raise_for_status(r)
        return True

    @staticmethod
    def _raise_for_status(r: httpx.Response) -> None:
        if r.is_success:
            return
        msg = f"dataset HTTP {r.status_code}"
        try:
            err = r.json().get("error", {})
            if err:
                msg = f"{err.get('code')}: {err.get('message')}"
        except Exception:  # тело может быть не-JSON
            pass
        raise DatasetError(msg)
