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

После `docker compose up -d --build` можно зарегистрировать агента из git-репозитория и дождаться билда Docker-образа. Для smoke-теста используем `agents/echo` через локальный bare-репозиторий, скопированный внутрь worker-контейнера.

### Подготовка bare-репозитория

```bash
cd /tmp
rm -rf echo-fixture echo-fixture.git
cp -R /root/agent_portal/agents/echo echo-fixture
cd echo-fixture
git init -b main
git -c user.name=t -c user.email=t@t add .
git -c user.name=t -c user.email=t@t commit -m init
cd /tmp
git clone --bare echo-fixture echo-fixture.git
docker cp /tmp/echo-fixture.git $(docker compose ps -q worker):/tmp/echo-fixture.git
```

### Сценарий

```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMeOnFirstLogin
BASE=http://localhost:8000
ORIGIN=http://localhost:8000
```

#### 1. Логин администратора

```bash
curl -s -c /tmp/cookies.txt -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: $ORIGIN" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"
```

#### 2. Регистрация агента (auto-enqueues build)

```bash
curl -s -b /tmp/cookies.txt -X POST "$BASE/api/admin/agents" \
  -H "Content-Type: application/json" \
  -H "Origin: $ORIGIN" \
  -d '{"git_url":"file:///tmp/echo-fixture.git","git_ref":"main"}' \
  | tee /tmp/agent.json
```

Ответ:

```json
{
  "agent": { "id": "<AGENT_ID>", "slug": "echo", "enabled": false, ... },
  "version": { "id": "<VERSION_ID>", "status": "pending_build" }
}
```

#### 3. Ожидание status=ready (polling)

```bash
VERSION_ID=$(python3 -c "import json; print(json.load(open('/tmp/agent.json'))['version']['id'])")

for i in $(seq 1 24); do
  STATUS=$(curl -s -b /tmp/cookies.txt -H "Origin: $ORIGIN" \
    "$BASE/api/admin/agent_versions/$VERSION_ID" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
  echo "[$i] status=$STATUS"
  [ "$STATUS" = "ready" ] && break
  [ "$STATUS" = "failed" ] && { echo "BUILD FAILED"; exit 1; }
  sleep 5
done
```

Worker слушает очередь `builds` в Redis, клонирует репо, валидирует `manifest.yaml`, генерирует Dockerfile (см. `apps/portal-worker/portal_worker/builder/dockerfile_gen.py`), инжектит portal-sdk и собирает образ через Docker daemon. Статусы: `pending_build` → `building` → `ready` (или `failed` с `build_error`+`build_log` в БД).

#### 4. Сделать версию current и включить агента

```bash
AGENT_ID=$(python3 -c "import json; print(json.load(open('/tmp/agent.json'))['agent']['id'])")

curl -s -b /tmp/cookies.txt -X POST -H "Origin: $ORIGIN" \
  "$BASE/api/admin/agent_versions/$VERSION_ID/set_current"

curl -s -b /tmp/cookies.txt -X PATCH \
  -H "Content-Type: application/json" \
  -H "Origin: $ORIGIN" \
  "$BASE/api/admin/agents/$AGENT_ID" \
  -d '{"enabled":true}'
```

#### 5. Проверка — public listing + Docker-образ

```bash
curl -s -b /tmp/cookies.txt -H "Origin: $ORIGIN" "$BASE/api/agents"
docker images | grep portal/agent-echo
```

Ожидается: `/api/agents` возвращает массив с echo, `docker images` показывает `portal/agent-echo:v<sha7>`.

### Failed-сценарий

Манифест с заведомо плохим `setup` (например, `pip install non-existent-pkg-xyz`) пишет в БД `status=failed`, `build_error=docker_error`, полный pip-лог в `build_log`. Регрессионный тест: `apps/portal-worker/tests/test_build_agent.py::test_build_with_bad_setup_writes_failed`.

### Заглянуть в очередь Redis напрямую

```bash
docker compose exec redis redis-cli lrange rq:queue:builds 0 -1
```

## Запуск задачи (1.2.3)

После того как агент `echo` зарегистрирован и в `status=ready` (см. предыдущий раздел), можно отправить ему job с input-файлами и наблюдать прогресс по WebSocket.

### Подготовка

```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMeOnFirstLogin
BASE=http://localhost:8000
ORIGIN=http://localhost:8000

curl -s -c /tmp/cookies.txt -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" -H "Origin: $ORIGIN" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"
```

### 1. Создать job (multipart с input-файлом)

```bash
echo "hello world" > /tmp/input.txt

curl -s -b /tmp/cookies.txt -X POST "$BASE/api/agents/echo/jobs" \
  -H "Origin: $ORIGIN" \
  -F 'params={"k":"v"}' \
  -F 'inputs[hello.txt]=@/tmp/input.txt' \
  | tee /tmp/job.json
```

Ответ:
```json
{"job": {"id": "<JOB_ID>", "status": "queued", "agent_slug": "echo"}}
```

### 2. Подключиться к WebSocket и наблюдать events

```bash
JOB_ID=$(python3 -c "import json; print(json.load(open('/tmp/job.json'))['job']['id'])")

# Извлечь cookie для wscat
COOKIE=$(awk -F'\t' '/portal_access/ {print $6"="$7}' /tmp/cookies.txt | head -1)

wscat -c "ws://localhost:8000/api/jobs/$JOB_ID/stream" \
  -H "Cookie: $COOKIE"
```

В WS видны events: `{"type":"resync","events":[...]}` (initial), затем построчно от агента (started/progress/result).

### 3. Опрос REST-фоллбэком (если без wscat)

```bash
for i in $(seq 1 24); do
  STATUS=$(curl -s -b /tmp/cookies.txt -H "Origin: $ORIGIN" \
    "$BASE/api/jobs/$JOB_ID" | python3 -c "import json,sys;print(json.load(sys.stdin)['status'])")
  echo "[$i] $STATUS"
  [ "$STATUS" = "ready" ] && break
  [ "$STATUS" = "failed" ] && { echo "FAILED"; exit 1; }
  sleep 2
done
```

### 4. Скачать output

```bash
# Detail endpoint не возвращает file_id — дёргаем через DB (psql) или ждём UI.
# Для CLI-демо — взять из admin-API в будущем; пока пример прямой ссылки:
curl -s -b /tmp/cookies.txt -H "Origin: $ORIGIN" \
  "$BASE/api/jobs/$JOB_ID/outputs/<FILE_ID>" \
  -o /tmp/output.bin
ls -lh /tmp/output.bin
```

### 5. Cancel посреди выполнения

```bash
curl -s -b /tmp/cookies.txt -X POST -H "Origin: $ORIGIN" \
  "$BASE/api/jobs/$JOB_ID/cancel"
# → {"id":"...","status":"cancelled"} (или running, если worker ещё не обработал флаг)
```

### Очередь Redis напрямую

```bash
docker compose exec redis redis-cli lrange rq:queue:jobs 0 -1
docker compose exec redis redis-cli pubsub channels 'job:*'
```
