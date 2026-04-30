# portal-api

Backend API портала AI-агентов МИРЭА. Часть моно-репо `mirea-agent-portal`.

## Установка для разработки

```bash
cd apps/portal-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Запуск тестов

```bash
pytest -v
```

## Запуск API локально

```bash
uvicorn portal_api.main:app --reload
```

Health-check: `curl http://localhost:8000/api/health`

Полный Quick start (с docker compose, регистрацией, логином) появится в Task 14 этого плана.
