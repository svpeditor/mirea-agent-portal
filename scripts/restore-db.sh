#!/usr/bin/env bash
# Восстановление Postgres портала из бэкапа.
#
# Использование:
#   ./scripts/restore-db.sh /var/backups/portal/portal-20260601-040000.sql.gz
#
# ВНИМАНИЕ: дропнет существующую базу `portal` и накатит из дампа.
# Перед запуском compose down api/worker, чтобы соединений не было.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup.sql.gz>" >&2
  exit 1
fi

BACKUP="$1"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-agent_portal}"

if [[ ! -f "$BACKUP" ]]; then
  echo "файл не найден: $BACKUP" >&2
  exit 1
fi

echo "[restore-db] восстановление из $BACKUP"
echo "[restore-db] ВНИМАНИЕ: текущая база 'portal' будет уничтожена."
read -r -p "продолжить? [yes/N] " ans
if [[ "$ans" != "yes" ]]; then
  echo "отмена"; exit 1
fi

# Останавливаем api/worker
docker compose -p "$COMPOSE_PROJECT" stop api worker || true

# DROP+CREATE через postgres user (имеет все права на portal db)
docker compose -p "$COMPOSE_PROJECT" exec -T postgres \
  psql -U portal -d postgres -c "DROP DATABASE IF EXISTS portal;"
docker compose -p "$COMPOSE_PROJECT" exec -T postgres \
  psql -U portal -d postgres -c "CREATE DATABASE portal OWNER portal;"

# Раскатываем дамп
gunzip -c "$BACKUP" | \
  docker compose -p "$COMPOSE_PROJECT" exec -T postgres psql -U portal -d portal

echo "[restore-db] done. Запусти api/worker: docker compose up -d"
