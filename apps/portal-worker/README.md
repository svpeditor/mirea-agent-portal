# portal-worker

RQ worker для сборки Docker-образов агентов (МИРЭА Agent Portal).

## Ответственности

- Потребляет очередь `builds` (Redis / RQ).
- При старте помечает все незавершённые `building`-версии как `failed` (`recover_orphaned_builds`).
- `build_agent_version(version_id)` — stub (Tasks 13-16).

## Переменные окружения

| Переменная | Пример | Описание |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://user:pass@db/portal` | Sync Postgres URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis broker |
| `PORTAL_SDK_PATH` | `/portal-sdk-src` | Путь к portal-sdk (опционально) |
| `BUILD_TIMEOUT_SECONDS` | `600` | Таймаут сборки |
| `BUILD_CLONE_TIMEOUT_SECONDS` | `60` | Таймаут git clone |
| `ALLOWED_BASE_IMAGES` | `["python:3.12-slim"]` | Whitelist base-images |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

## Установка и запуск

```bash
cd apps/portal-worker
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# Запуск worker
DATABASE_URL=postgresql+psycopg2://... REDIS_URL=redis://... python -m portal_worker.main
```

## Тесты

```bash
pytest -v
```

## Линтеры

```bash
ruff check .
mypy portal_worker/
```

## Docker

Собирается из корня монорепо (Task 17):

```bash
docker compose build worker
docker compose up worker
```
