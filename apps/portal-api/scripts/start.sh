#!/bin/sh
# apps/portal-api/scripts/start.sh
set -e

echo "[start.sh] Запуск миграций..."
alembic upgrade head

echo "[start.sh] Старт uvicorn..."
if [ -n "$RELOAD" ]; then
    exec uvicorn portal_api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/portal_api
else
    exec uvicorn portal_api.main:app --host 0.0.0.0 --port 8000
fi
