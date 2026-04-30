# mirea-agent-portal

Платформа AI-агентов кафедры в рамках НУГ «Цифровые технологии в математическом образовании», МИРЭА.

Веб-портал, через который преподаватели запускают AI-агентов на своих задачах **без знания командной строки и без установки Python**. Студенты-разработчики НУГ пишут новых агентов под опубликованный контракт — портал автоматически их подхватывает.

## Статус

🟡 **Pre-MVP — дизайн зафиксирован, имплементация не начата.**

- ✅ Спек 1 «Фундамент платформы» — написан и закоммичен
- ⏳ План реализации Спека 1 — в работе
- ⏳ Имплементация — не начата

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
