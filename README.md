# mirea-agent-portal

Платформа AI-агентов кафедры в рамках НУГ «Цифровые технологии в математическом образовании», МИРЭА.

Веб-портал, через который преподаватели запускают AI-агентов на своих задачах **без знания командной строки и без установки Python**. Студенты-разработчики НУГ пишут новых агентов под опубликованный контракт — портал автоматически их подхватывает.

## Статус

🟢 **План 1.1 закрыт. SDK v0.1.0 опубликован.**

- ✅ Спек 1 «Фундамент платформы» — написан и закоммичен
- ✅ План 1.1 — Контракт + Python-SDK + echo-агент (tag `sdk-v0.1.0`)
- ✅ План 1.2 — Backend API + Job Queue + Docker-runner + LLM-прокси (1.2.1-1.2.4)
- 🟡 План 1.3 — Frontend (PR #6)
- 🟡 План 1.4 — Перенос реальных агентов:
  - milestone-0: stub-агенты `agents/proverka_stub/` и `agents/science_agent_stub/` (PR #11)
  - milestone-1: real-код после ОК владельца платформы

Команда «агенты» может начинать писать агентов прямо сейчас:
- **Гид разработчика**: [`docs/agent-developer-guide.md`](docs/agent-developer-guide.md)
- Контракт: [`docs/contract.md`](docs/contract.md)
- JSON Schema для IDE: [`docs/manifest.schema.json`](docs/manifest.schema.json)
- Установить SDK: `pip install -e ./packages/portal-sdk-python`
- Скопировать `agents/echo/` как шаблон
- Проверить манифест: `portal-sdk-validate-manifest .`
- Запустить локально: `portal-sdk-run-local <agent_dir>`

Деплой: см. [`docs/deploy-guide.md`](docs/deploy-guide.md).

## Что есть в репо

```
docs/superpowers/specs/   # design-доки по спекам
  2026-04-30-agent-platform-foundation-design.md   ← Спек 1, текущий
docs/superpowers/mockups/ # HTML-макеты UI с брейнштормa
```

Когда стартует имплементация — здесь появятся:

```
apps/portal-frontend/        # Next.js + TS + Tailwind + shadcn/ui (план 1.3, PR #6)
apps/portal-api/             # FastAPI + Pydantic + SQLAlchemy async
apps/portal-worker/          # RQ + Docker SDK
packages/portal-sdk-python/  # SDK для писателей агентов
agents/echo/                 # reference-имплементация агента
agents/proverka_stub/        # stub под proverka (план 1.4 milestone-0)
agents/science_agent_stub/   # stub под science_agent (план 1.4 milestone-0)
scripts/                     # backup-db.sh / restore-db.sh
.github/workflows/           # CI
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
