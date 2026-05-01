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
