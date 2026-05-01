# portal-api

Backend API портала AI-агентов МИРЭА. Часть моно-репо `mirea-agent-portal`.

## Quick start через docker compose

```bash
cd /root/agent_portal
cp .env.example .env
# В .env заполнить JWT_SECRET (openssl rand -base64 64) и INITIAL_ADMIN_*

docker compose up -d --build
curl http://localhost:8000/api/health
```

## Полный E2E-сценарий через curl

```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMeOnFirstLogin

# 1. Логин админа
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"

# 2. Создание invite
curl -b cookies.txt -X POST http://localhost:8000/api/admin/invites \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d '{"email":"student@example.com"}'
# → возвращает {token, expires_at, registration_url}

# 3. Регистрация юзера по invite
curl -c student.txt -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d '{"token":"<token-из-шага-2>","email":"student@example.com","display_name":"Студент","password":"StudentPass1"}'

# 4. Логин юзера
curl -c student.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d '{"email":"student@example.com","password":"StudentPass1"}'

# 5. Получение /api/me
curl -b student.txt http://localhost:8000/api/me

# 6. Refresh-токен
curl -b student.txt -c student.txt -X POST http://localhost:8000/api/auth/refresh \
  -H "Origin: http://localhost:8000"

# 7. Reuse-attack (должен вернуть REFRESH_REUSE_DETECTED)
# … взять старый refresh из student.txt до шага 6 и повторить /refresh с ним

# 8. Logout
curl -b student.txt -X POST http://localhost:8000/api/auth/logout \
  -H "Origin: http://localhost:8000"

# 9. Reset-password от админа
curl -b cookies.txt -X POST "http://localhost:8000/api/admin/users/<student-id>/reset-password" \
  -H "Origin: http://localhost:8000"
# → возвращает {"temporary_password": "..."} — админ передаёт пользователю
```

## Установка для локальной разработки (без Docker)

```bash
cd apps/portal-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

Чтобы запустить API локально без Docker — нужен Postgres. Самый простой способ: поднять только postgres из compose:

```bash
cd /root/agent_portal
docker compose up -d postgres
cd apps/portal-api
DATABASE_URL=postgresql+asyncpg://portal:portal@localhost:5432/portal \
  JWT_SECRET=$(openssl rand -base64 64) \
  INITIAL_ADMIN_EMAIL=admin@example.com \
  INITIAL_ADMIN_PASSWORD=ChangeMe \
  alembic upgrade head
DATABASE_URL=postgresql+asyncpg://portal:portal@localhost:5432/portal \
  JWT_SECRET=... \
  INITIAL_ADMIN_EMAIL=admin@example.com \
  INITIAL_ADMIN_PASSWORD=ChangeMe \
  uvicorn portal_api.main:app --reload
```

## Структура

| Каталог | Что |
|---|---|
| `portal_api/main.py` | FastAPI app, middleware, exception handlers |
| `portal_api/config.py` | Settings через pydantic-settings |
| `portal_api/db.py` | AsyncEngine + session factory |
| `portal_api/models/` | SQLAlchemy ORM (User, Invite, RefreshToken) |
| `portal_api/schemas/` | Pydantic DTO для API |
| `portal_api/routers/` | health / auth / me / admin_users / admin_invites |
| `portal_api/services/` | Бизнес-логика (auth_service, user_service, invite_service) |
| `portal_api/core/` | security (JWT/bcrypt), exceptions, logging, origin middleware |
| `alembic/` | Миграции БД |
| `tests/` | pytest + testcontainers Postgres |

## Регистрация агента (1.2.2)

После `docker compose up -d --build` можно зарегистрировать агента и запустить сборку образа.

### Предварительные условия

```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMeOnFirstLogin
BASE=http://localhost:8000
```

### 1. Логин администратора

```bash
curl -s -c admin.txt -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"
# → {"user": {"id": "...", "email": "...", "role": "admin", ...}}
```

### 2. Регистрация агента (загрузка manifest.yaml)

```bash
curl -s -b admin.txt -X POST "$BASE/api/admin/agents" \
  -H "Origin: http://localhost:8000" \
  -F "manifest=@agents/echo/manifest.yaml" \
  -F "source_zip=@agents/echo/echo.zip"
# → {"id": "<AGENT_ID>", "slug": "echo", "status": "pending", ...}
```

Сохраните `id` из ответа:

```bash
AGENT_ID=<id-из-ответа-выше>
```

### 3. Запуск сборки образа

```bash
curl -s -b admin.txt -X POST "$BASE/api/admin/agents/$AGENT_ID/build" \
  -H "Origin: http://localhost:8000"
# → {"build_id": "<BUILD_ID>", "status": "queued"}
```

### 4. Опрос статуса сборки

```bash
curl -s -b admin.txt "$BASE/api/admin/agents/$AGENT_ID/builds/latest" \
  -H "Origin: http://localhost:8000"
# → {"status": "success", "image_tag": "portal/agent-echo:v<sha7>", ...}
```

Worker (RQ) получает задачу из Redis, клонирует исходники, генерирует Dockerfile
(см. `apps/portal-worker/portal_worker/builder/dockerfile_gen.py`), инжектит portal-sdk
и собирает образ через Docker daemon. Статус обновляется в БД — `queued` → `building`
→ `success` (или `failed` с логом ошибки).

### 5. Список агентов

```bash
curl -s -b admin.txt "$BASE/api/admin/agents" \
  -H "Origin: http://localhost:8000"
# → [{"id": "...", "slug": "echo", "status": "ready", ...}]
```

### Проверка очереди Redis напрямую

```bash
docker compose exec redis redis-cli lrange rq:queue:default 0 -1
```
