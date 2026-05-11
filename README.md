# mirea-agent-portal

Платформа AI-агентов кафедры в рамках НУГ «Цифровые технологии в математическом образовании», МИРЭА.

Веб-портал, через который преподаватели запускают AI-агентов на своих задачах **без знания командной строки и без установки Python**. Студенты-разработчики НУГ пишут новых агентов под опубликованный контракт — портал автоматически их подхватывает.

## Статус

🟢 **Спек 1 «Фундамент» технически готов.** Demo-инстанс работает.

- ✅ План 1.1 — Контракт + Python-SDK + echo-агент (tag `sdk-v0.1.0`)
- ✅ План 1.2 — Backend API + Job Queue + Docker-runner + LLM-прокси
- ✅ План 1.3 — Frontend (merged: PR #6)
- ✅ План 1.4 — Реальные агенты:
  - [`mirea-agent-portal-proverka`](https://github.com/svpeditor/mirea-agent-portal-proverka) — проверка конкурсных работ через DeepSeek-R1
  - [`mirea-agent-portal-science`](https://github.com/svpeditor/mirea-agent-portal-science) — поиск научных статей через DeepSeek-R1

Команда «агенты» — пишут агентов:
- **Гид разработчика**: [`docs/agent-developer-guide.md`](docs/agent-developer-guide.md)
- Контракт: [`docs/contract.md`](docs/contract.md)
- JSON Schema для IDE: [`docs/manifest.schema.json`](docs/manifest.schema.json)
- Установить Python SDK: `pip install -e ./packages/portal-sdk-python`
- Или TypeScript SDK: `npm install ./packages/portal-sdk-ts`
- Скопировать `agents/echo/` как шаблон
- Проверить манифест: `portal-sdk-validate-manifest .`
- Запустить локально: `portal-sdk-run-local <agent_dir>`

Деплой: [`docs/deploy-guide.md`](docs/deploy-guide.md).

## Что есть в репо

```
docs/superpowers/specs/   # design-доки по спекам
  2026-04-30-agent-platform-foundation-design.md   ← Спек 1, текущий
docs/superpowers/mockups/ # HTML-макеты UI с брейнштормa
```

Когда стартует имплементация — здесь появятся:

```
apps/portal-frontend/     # Next.js + TS + Tailwind + shadcn/ui
apps/portal-api/          # FastAPI + Pydantic + SQLAlchemy async
apps/portal-worker/       # RQ + Docker SDK
packages/portal-sdk-python/  # SDK для писателей агентов
agents/echo/              # reference-имплементация агента
agents/proverka/          # перенесённый proverka под новый контракт
```

## Команды

- **Команда «Портал»** — frontend, API, worker, SDK, админка, OpenRouter-прокси, auth, квоты, деплой
- **Команда «Агенты»** — echo (reference), перенос proverka, в Спеке 2 — science_agent, в Спеке 3 — поиск научных статей

## Tech-stack

- **Frontend** Next.js 15 + TypeScript + Tailwind + shadcn/ui
- **Backend** FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + Postgres 16
- **Очередь** RQ + Redis
- **Sandbox** Docker per job (через Docker SDK для Python)
- **LLM-gateway** OpenRouter через прокси портала
- **Деплой** Docker Compose, на старте — Mac Mini M4

Подробности и обоснования — в спеке.

## Конвенция репозиториев

- **Этот репо (моно)** — платформа: portal, SDK, reference-агенты (echo, echo-ts)
- **Per-agent репо** — каждый продакшен-агент живёт в отдельном репозитории, добавляется в админку портала через Git URL

### Действующие production-агенты

| Агент | Репозиторий | Что делает |
|---|---|---|
| **proverka** | [svpeditor/mirea-agent-portal-proverka](https://github.com/svpeditor/mirea-agent-portal-proverka) | Принимает папку PDF/DOCX, разбирает каждую работу через DeepSeek-R1 по чек-листу научной экспертизы, возвращает сводный Word + zip заключений |
| **science-agent** | [svpeditor/mirea-agent-portal-science](https://github.com/svpeditor/mirea-agent-portal-science) | По теме исследования спрашивает у DeepSeek-R1 список релевантных публикаций, формирует Word-отчёт + BibTeX |
| **echo** | `agents/echo/` (в моно) | Тестовый агент для smoke-проверки SDK и портала |

### Подключить нового агента к порталу

1. Создать репозиторий с `manifest.yaml` + `agent.py` (контракт SDK см. `docs/contract.md`)
2. Запушить на GitHub
3. Под админом — `POST /api/admin/agents`:

   ```bash
   curl -X POST $PORTAL/api/admin/agents \
     -H 'Origin: ...' -b /tmp/admin.cookie \
     -H 'Content-Type: application/json' \
     -d '{"git_url":"https://github.com/USER/REPO.git","git_ref":"main"}'
   ```
4. Дождаться `status=ready` у новой версии: `GET /api/admin/agents/<id>/versions`
5. `POST /api/admin/agent_versions/<vid>/set_current`
6. `PATCH /api/admin/agents/<id>` с `{"enabled":true}`

### Сеть агента и ограничения

Контейнер агента стоит в изолированной docker-сети (`portal-agents-net`, `internal: true`) — это **намеренно**. Что это значит:

- ❌ нет доступа в публичный интернет (arXiv API, Semantic Scholar, любые HTTP-запросы наружу)
- ❌ нельзя «телефонить домой», вытащить секреты из контейнера, скачать payload
- ✅ доступен только LLM-прокси `portal-api` (через `OPENROUTER_BASE_URL` и ephemeral `OPENROUTER_API_KEY`)
- ✅ читает `$INPUT_DIR/*` (read-only), пишет в `$OUTPUT_DIR/*`

Поэтому `science-agent` опирается на знания LLM, а не ходит в arXiv напрямую. Если нужен live-поиск, на стороне `portal-api` нужно добавить allowlist-proxy endpoint (например `/api/sandbox/arxiv?q=...`) — это вне scope wave0.

## Roadmap

| Спек | Содержимое | Команда |
|---|---|---|
| **1. Фундамент** | Контракт агента + портал-MVP + перенос proverka | Портал + Агенты |
| 2. science_agent | Перенос второго существующего агента + полировка контракта | Агенты |
| 3. Поиск статей | Новый агент: arXiv + Semantic Scholar + Crossref | Агенты |
| 4. Конструктор | Полноценный визуальный конструктор агентов через UI | Портал |
| 5. SDK + доки | SDK на других языках, документация для писателей агентов | Портал (parallel) |

## Frontend (Next.js)

Frontend живёт в `apps/portal-frontend/`. Запуск:

```bash
docker compose up -d frontend
# или для dev:
cd apps/portal-frontend && npm run dev
```

Открывается на http://localhost:3000. Бэкенд должен быть на :8000 (`docker compose up api`).

См. `apps/portal-frontend/README.md` для подробностей.
