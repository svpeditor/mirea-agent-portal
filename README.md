# mirea-agent-portal

Платформа AI-агентов кафедры в рамках НУГ «Цифровые технологии в математическом образовании», МИРЭА.

Веб-портал, через который преподаватели запускают AI-агентов на своих задачах **без знания командной строки и без установки Python**. Студенты-разработчики НУГ пишут новых агентов под опубликованный контракт — портал автоматически их подхватывает.

## Статус

🟢 **Спек 1 «Фундамент» технически готов.** Demo-инстанс работает.

- ✅ План 1.1 — Контракт + Python-SDK + echo-агент (tag `sdk-v0.1.0`)
- ✅ План 1.2 — Backend API + Job Queue + Docker-runner + LLM-прокси
- ✅ План 1.3 — Frontend (PR #6 — пока на review)
- 🟡 План 1.4 — Перенос реальных агентов:
  - milestone-0: stub-агенты `agents/proverka_stub/` и `agents/science_agent_stub/` опубликованы
  - milestone-1: real-код — ждёт ОК от куратора НУГ (см. `QUESTIONS_FOR_DANYA.md`)

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

- **Этот репо (моно)** — платформа: portal, SDK, reference-агенты (echo, proverka)
- **Per-agent репо** — каждый студенческий агент живёт в своём репозитории, добавляется в админку портала через Git URL

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
