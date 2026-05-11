#!/usr/bin/env bash
# Backup Postgres портала.
#
# Использование:
#   BACKUP_DIR=/var/backups/portal ./scripts/backup-db.sh
#
# Опционально: BACKUP_S3_URI=s3://bucket/portal — после локального dump'а
# заливает в S3 (требует aws cli + IAM-creds в env). Локальная ротация
# держит последние BACKUP_KEEP=14 файлов.
#
# Запуск через cron на хосте:
#   0 4 * * * cd /opt/agent_portal && BACKUP_DIR=/var/backups/portal ./scripts/backup-db.sh >> /var/log/portal-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/portal}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
BACKUP_S3_URI="${BACKUP_S3_URI:-}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-agent_portal}"

mkdir -p "$BACKUP_DIR"

ts="$(date -u +%Y%m%d-%H%M%S)"
out="$BACKUP_DIR/portal-${ts}.sql.gz"

echo "[backup-db] dump → $out"

# pg_dump через docker compose (нет нужды в host-postgres-tools)
docker compose -p "$COMPOSE_PROJECT" exec -T postgres \
  pg_dump -U portal -d portal --no-owner --no-privileges \
  | gzip -c > "$out"

size=$(stat -c%s "$out" 2>/dev/null || stat -f%z "$out")
echo "[backup-db] ok: $out (${size} bytes)"

# Ротация локальных бэкапов
ls -1t "$BACKUP_DIR"/portal-*.sql.gz 2>/dev/null \
  | tail -n +$((BACKUP_KEEP + 1)) \
  | xargs -r rm -v

if [[ -n "$BACKUP_S3_URI" ]]; then
  echo "[backup-db] upload → $BACKUP_S3_URI/$(basename "$out")"
  aws s3 cp "$out" "$BACKUP_S3_URI/$(basename "$out")"
fi

echo "[backup-db] done"
