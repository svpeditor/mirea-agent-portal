# Гид по развёртыванию

Документация для оператора, который ставит портал на свой сервер.

## Требования

- Linux-сервер: Ubuntu 24.04 / Debian 12 / любой дистрибутив с Docker.
- Docker Engine ≥ 24 + Docker Compose v2.
- ~10 GB свободного места: postgres + portal_files + docker images.
- ~2 GB RAM минимум, 4 GB рекомендуется (worker + agent containers).
- Открытые наружу порты: 80, 443. Внутренние 5432/6379/8000 не выпускать.

## Первая установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/svpeditor/mirea-agent-portal.git /opt/agent_portal
cd /opt/agent_portal
```

### 2. Подготовить `.env`

Создай `.env` в корне с минимальным набором:

```bash
# Секреты
JWT_SECRET=$(openssl rand -hex 32)
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=$(openssl rand -base64 24)

# OpenRouter (если планируется LLM-агенты)
OPENROUTER_API_KEY=sk-or-v1-...
LLM_ALLOWED_MODELS=deepseek/deepseek-r1,anthropic/claude-haiku-4-5-20251001

# Окружение
ENVIRONMENT=prod
COOKIE_SECURE=true

# Sentry (опционально)
SENTRY_DSN=https://<key>@sentry.example.com/<project>
SENTRY_RELEASE=portal-0.1.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

ENV читает `apps/portal-api/portal_api/config.py` и `apps/portal-worker/portal_worker/config.py`. См. их Pydantic Settings для полного списка.

### 3. Подготовить хост

```bash
sudo mkdir -p /var/portal-files /var/backups/portal
sudo chmod 777 /var/portal-files  # worker mount'ит сюда output_dir агентов
```

### 4. Собрать и запустить

```bash
docker compose up -d --build
```

Compose поднимет: postgres, redis, api, worker (+ frontend после merge PR #6).

Alembic миграции прогоняются автоматически на старте api. Worker имеет `restart: on-failure:3` (см. PR #9), чтобы пережить race с миграциями на cold start.

### 5. Проверить здоровье

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}

curl http://localhost:8000/api/health/full
# {"status":"ok","checks":{"postgres":"ok","redis":"ok"},"uptime_seconds":...}
```

### 6. Обратный прокси / TLS

Перед api поставь nginx или caddy. Минимум — Let's Encrypt + проксирование 443→8000. Для устойчивости к ТСПУ-фильтру Cloudflare edge — рассмотри Yandex Cloud relay.

Cookies в проде должны идти `Secure` (`COOKIE_SECURE=true`). Origin-check срабатывает автоматически — добавь свой домен в `ALLOWED_ORIGINS`.

## Бэкапы

`scripts/backup-db.sh` делает `pg_dump | gzip` и оставляет последние 14 файлов:

```bash
sudo mkdir -p /var/backups/portal
BACKUP_DIR=/var/backups/portal /opt/agent_portal/scripts/backup-db.sh
```

Cron на 4:00 UTC ежедневно:

```cron
0 4 * * * cd /opt/agent_portal && BACKUP_DIR=/var/backups/portal ./scripts/backup-db.sh >> /var/log/portal-backup.log 2>&1
```

S3-копирование — через `BACKUP_S3_URI`:

```bash
BACKUP_S3_URI=s3://my-bucket/portal /opt/agent_portal/scripts/backup-db.sh
```

(требуется `aws s3 cp` + IAM-credentials в env).

`portal_files` (input/output задач) бэкапить отдельно через `rsync` или `restic`. Эти данные не критичны — задачи можно перезапустить.

## Восстановление из бэкапа

```bash
./scripts/restore-db.sh /var/backups/portal/portal-20260601-040000.sql.gz
```

Скрипт остановит api/worker, дропнет базу и накатит дамп. После — `docker compose up -d`.

## Обновление

```bash
cd /opt/agent_portal
git pull
docker compose build api worker
docker compose up -d  # alembic upgrade head запустится автоматически
```

Перед обновлением желательно сделать backup. Если что-то пошло не так — `restore-db.sh` + откат на предыдущий тэг `git checkout <prev>` + rebuild.

## Мониторинг

- **Логи**: `docker compose logs -f api worker`. JSON-формат через structlog.
- **Sentry**: задай `SENTRY_DSN`, ошибки автоматически уйдут.
- **Health**: cron-проверка `/api/health/full` через мониторинг (Uptime Robot, Pingdom, etc.).
- **Disk**: следи за `/var/portal-files`; long-running агенты могут наплодить артефактов.

## Чек-лист продакшен-готовности

- [ ] `JWT_SECRET` случайный 64-символьный hex (`openssl rand -hex 32`).
- [ ] `INITIAL_ADMIN_PASSWORD` — длинный (`openssl rand -base64 24`), сразу после первого логина смени через UI.
- [ ] `COOKIE_SECURE=true`, домен в `ALLOWED_ORIGINS` без http://.
- [ ] `ENVIRONMENT=prod` (отключает dev-индикаторы).
- [ ] `OPENROUTER_API_KEY` живой, `LLM_ALLOWED_MODELS` явный whitelist.
- [ ] Backup-cron настроен.
- [ ] TLS перед api (nginx + Let's Encrypt).
- [ ] Sentry или другой error-tracker подключён.
- [ ] Disk-alerting на `/var/portal-files` и `/var/lib/docker`.
- [ ] `/var/portal-files` chmod 777 (worker'у нужен write).

## Откат

Для откатимости держи старый `docker images` тэг + последний `*.sql.gz`. Минимально:

```bash
git checkout <prev-tag>
docker compose build api worker
./scripts/restore-db.sh /var/backups/portal/<prev-backup>.sql.gz
docker compose up -d
```

## Известные грабли

- **Cloudflare edge** режется ТСПУ из РФ. Если бот падает с TLS handshake EOF — проверь tunnel, может надо пускать через Yandex Cloud relay.
- **Alembic migration вход в worker race** — фикс `restart: on-failure:3` в PR #9.
- **Cookie path /api → /** меняли в PR #6 frontend; после merge все существующие сессии сбросятся.
- **OpenRouter timeout** — image-модели не успевают за 120с. Прокси конфигурится `LLM_REQUEST_TIMEOUT_SECONDS`, дефолт 30с подходит для chat-completions; для image-моделей — поднять.
