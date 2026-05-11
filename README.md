# mirea-agent-portal

Платформа AI-агентов кафедры в рамках НУГ «Цифровые технологии в математическом образовании», МИРЭА.

Веб-портал, через который преподаватели запускают AI-агентов на своих задачах **без знания командной строки и без установки Python**. Студенты-разработчики НУГ пишут новых агентов под опубликованный контракт — портал автоматически их подхватывает.

## Статус

🟢 **Спек 1 «Фундамент» технически готов.** Demo-инстанс работает.

- ✅ План 1.1 — Контракт + Python-SDK + echo-агент (tag `sdk-v0.1.0`)
- ✅ План 1.2 — Backend API + Job Queue + Docker-runner + LLM-прокси
- ✅ План 1.3 — Frontend (PR #6)
- ✅ План 1.4 — Реальные агенты (4 production-агента, см. ниже)
- ✅ План 1.5 — Sandbox-прокси (arXiv/Crossref/S2), аватары, профиль, mobile responsive
- ✅ План 1.6 — Per-agent quotas, email-уведомления, cron-расписания
- ✅ План 1.7 — UI-конструктор агента (Мастер + ZIP-upload), без CLI

## Гиды

- 👨‍🏫 **Гид администратора** (без программирования): [`docs/admin-guide.md`](docs/admin-guide.md) — 3 способа добавить агента через UI со скриншотами.
- 👨‍💻 **Гид разработчика**: [`docs/agent-developer-guide.md`](docs/agent-developer-guide.md) — как писать своих агентов под контракт SDK.
- 📐 **Контракт**: [`docs/contract.md`](docs/contract.md) + [`docs/manifest.schema.json`](docs/manifest.schema.json).
- 🚀 **Деплой**: [`docs/deploy-guide.md`](docs/deploy-guide.md).

## Действующие production-агенты

| Агент | Репозиторий | Что делает |
|---|---|---|
| **proverka** | [svpeditor/mirea-agent-portal-proverka](https://github.com/svpeditor/mirea-agent-portal-proverka) | Принимает папку PDF/DOCX школьных работ → DeepSeek-R1 разбирает по чек-листу научной экспертизы → сводный Word + zip per-work заключений. |
| **science-agent** | [svpeditor/mirea-agent-portal-science](https://github.com/svpeditor/mirea-agent-portal-science) | По теме ищет статьи в arXiv (через sandbox-прокси), enrichment через Crossref+Semantic Scholar (citations, DOI), DeepSeek-R1 ранжирует + аннотации ~5 предложений + обоснование балла. Сортировка по релевантности или цитированиям. Прямая ссылка на PDF. |
| **article-analyzer** | [svpeditor/mirea-agent-portal-article-analyzer](https://github.com/svpeditor/mirea-agent-portal-article-analyzer) | Папка PDF/DOCX готовых статей + научная тема → разбор каждой (метаданные APA+ГОСТ, проблема/методология/результаты, 3-5 ключевых цитат с переводом, score 0-10 + обоснование, обобщение top-статей). |
| **translator** | [svpeditor/mirea-agent-portal-translator](https://github.com/svpeditor/mirea-agent-portal-translator) | DOCX/текст научной работы → перевод на ru/en/zh через DeepSeek-R1 с сохранением структуры и опциональным глоссарием. |
| **echo** | `agents/echo/` (в моно) | Reference-агент для smoke-проверки SDK. |

## Как добавить нового агента

Три способа через **`/admin/agents` → + Создать агент**:

### 1. Мастер (для не-разработчиков)
Визуальная форма: slug + name + категория + inputs/outputs → портал генерит boilerplate (`manifest.yaml` + `agent.py` + `Dockerfile`) → собирает образ. Логику дописываете отдельно.

### 2. ZIP-архив (готовый код, без GitHub)
Drag-drop `.zip` с `manifest.yaml` + кодом. Лимит 50 МБ. Защита от zip-slip, auto-flatten одной top-папки.

### 3. Git URL (для опытных)
`https://github.com/...` + git_ref. Удобно для итеративной разработки.

После создания → дождаться `status=ready` → «Сделать текущей» → «Включить». Подробно со скриншотами — [`docs/admin-guide.md`](docs/admin-guide.md).

## Sandbox endpoints (egress для агентов)

Контейнеры агентов изолированы в `portal-agents-net` (`internal: true`) — нет прямого доступа в интернет. Доступны только sandbox-endpoints на `portal-api`:

| Endpoint | Источник | Описание |
|---|---|---|
| `GET /api/sandbox/arxiv?search_query=...` | arXiv API | Реальный поиск статей, Atom-feed парсится в JSON |
| `GET /api/sandbox/crossref?query=...` | Crossref Works API | DOI + citation counts + journal venue |
| `GET /api/sandbox/semantic-scholar?query=...` | Semantic Scholar | Abstracts + citation counts + DOI |
| `POST /llm/v1/chat/completions` | OpenRouter (через прокси) | LLM-вызовы, ephemeral-токен, квоты per-user/per-agent |

Auth: bearer ephemeral-токен (инжектится порталом). Origin middleware exempt. Spec для писателей агентов — [`docs/agent-developer-guide.md`](docs/agent-developer-guide.md).

## Возможности портала

### Для пользователей
- Каталог агентов по категориям (научная / учебная / организационная)
- Запуск через браузерную форму, прогресс в реальном времени по WebSocket
- Скачивание артефактов (Word/PDF/JSON/ZIP)
- История запусков с пагинацией и фильтрами
- Личный кабинет: аватар, имя, email-уведомления о завершении job
- Mobile responsive (топбар → dropdown, таблицы скроллятся)

### Для администраторов
- Управление вкладками каталога (`/admin/tabs`)
- Регистрация агентов: Мастер / ZIP / Git URL (`/admin/agents`)
- Версионирование агентов (можно откатиться)
- Per-user квоты (месячный лимит, per-job cap) + per-agent cost cap
- Аватары других юзеров в `/admin/users`
- Cron-расписания (hourly/daily/weekly/monthly) для авто-запусков (`/admin/crons`)
- LLM-usage агрегаты (`/admin/usage`), audit log (`/admin/audit`)
- System dashboard ping postgres+redis (`/admin/system`)

### Для разработчиков агентов
- SDK на Python (`portal-sdk-python`) и TypeScript (`portal-sdk-ts`)
- Language-agnostic контракт (yaml + NDJSON stdout)
- `portal-sdk-validate-manifest` + `portal-sdk-run-local` CLI
- 70+ юнит-тестов backend + frontend

## Tech-stack

- **Frontend** Next.js 15 + TypeScript + Tailwind + shadcn/ui
- **Backend** FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + Postgres 16
- **Очередь** RQ + Redis
- **Sandbox** Docker per job (через Docker SDK для Python)
- **LLM-gateway** OpenRouter через прокси портала, ephemeral-токены
- **Cron** Worker daemon-thread, SELECT FOR UPDATE SKIP LOCKED
- **Email** SMTP, graceful no-op без `SMTP_HOST`
- **Деплой** Docker Compose, demo на Mac Mini M4

## Структура репо

```
apps/portal-frontend/         Next.js 15 + TypeScript
apps/portal-api/              FastAPI + SQLAlchemy async
  alembic/versions/           Миграции 0001..0009
apps/portal-worker/           RQ worker + cron scheduler + builder
packages/portal-sdk-python/   SDK + manifest schema
packages/portal-sdk-ts/       1:1 TS-эквивалент
agents/echo/                  Reference Python агент
agents/echo-ts/               Reference TS агент
docs/
  admin-guide.md              Для администратора кафедры
  agent-developer-guide.md    Для писателей агентов
  contract.md                 Спецификация контракта
  manifest.schema.json        JSON Schema для IDE
  deploy-guide.md             Production-деплой
  screenshots/                К admin-guide
```

## Запуск локально

```bash
# Backend + worker + frontend + postgres + redis
docker compose up -d

# Открыть
open http://localhost:3000

# Логи
docker compose logs -f api worker
```

Демо: `http://100.106.180.108:3000/` (через tailscale).

## Roadmap

| Спек | Статус | Что |
|---|---|---|
| **1. Фундамент** | ✅ | Контракт + портал-MVP + 4 production-агента |
| **2-3. Перенос реальных агентов** | ✅ | proverka, science, article-analyzer, translator |
| **4. UI-конструктор** | ✅ | Мастер + ZIP + Git URL flow в админке |
| **5. Расширения** | ✅ | Avatars, profile, cron, email, per-agent quota, sandbox endpoints |
| 6. Дополнительные источники | ⏸ | NASA ADS, OpenAlex, e-library через прокси |
| 7. Production-деплой | ⏸ | Hetzner + домен (вне scope demo) |

См. `CHANGELOG.md` для деталей.
