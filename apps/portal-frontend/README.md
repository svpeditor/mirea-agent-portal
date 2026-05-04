# portal-frontend

Next.js 15 frontend для портала НУГ. Дизайн в editorial-стиле школы Anthropic: paper фон, сериф (Source Serif 4), rust accent (#c14a2c).

## Архитектура

- **App Router** с groups `(public)` / `(app)` / `(admin)` для разделения auth-зон
- **Server Components** для data fetching через `lib/api/server.ts` (cookies из request)
- **TanStack Query** для client mutations и polling (auto-poll build status в админке)
- **WebSocket** для live job progress с reconnect logic (1s backoff, since-cursor)
- **Cookie auth** через middleware с silent refresh
- **shadcn/ui** компоненты, форк, override через CSS-переменные
- **next/font/google** self-hosting фонтов с subset cyrillic

## Local dev

```bash
cp .env.example .env
npm install
npm run dev
```

Фронт стартует на http://localhost:3000. Бэкенд должен быть запущен на http://localhost:8000:

```bash
docker compose up -d postgres redis api
```

Dev-rewrite в `next.config.ts` проксирует `/api/*` → `localhost:8000/api/*`, чтобы cookies + CORS работали без хедакейка.

## Codegen API types

```bash
npm run codegen
# регенерит lib/api/types.ts из http://localhost:8000/openapi.json
```

Пока бэкенд не поднят используется ручной fallback в `lib/api/types.ts`.

## Tests

- `npm run lint` — ESLint + tsc --noEmit (0 errors required)
- `npm test` — Vitest unit (jsdom): 29 тестов покрывают `mapApiError`, `wsUrl`, `refreshTokens`, `buildZodSchema`, `AgentForm`, `FileUpload`, `useJobWebSocket`
- `npm run test:e2e` — Playwright e2e (требует backend + seed данные)

E2E env-переменные см. `.env.example` секцию `E2E_*`. Браузеры: `npx playwright install chromium`.

## Build & Deploy

Production build:
```bash
npm run build
npm start
```

Через Docker:
```bash
# из корня монорепо:
docker compose build frontend
docker compose up -d frontend
```

Frontend сидит в `portal-net`, обращается к бэкенду по DNS `api:8000`. Внешний порт 3000 опубликован.

## Дизайн-система

CSS-vars в `app/globals.css` (`@theme inline`), экспорт в JS через `lib/design-tokens.ts`. Палитра — paper/secondary/tertiary бэкграунд, sepia текст в трёх уровнях, rust accent с distinct firebrick error. shadcn/ui компоненты в `components/ui/` — все цвета через `bg-[color:var(--color-*)]`, фокус-ринги через global rule + per-component override на формах.

После Wave 0 финал палитры/шрифтов делается через `/design-consultation` skill.

## Структура

- `app/(public)` — landing, login, register-by-invite
- `app/(app)` — agents catalog, agent detail, jobs list, job detail, profile (auth-gated)
- `app/(admin)` — users, agents, tabs, usage (admin-gated)
- `components/ui/` — shadcn primitives (17 компонентов)
- `components/agent-form/` — динамическая форма по `manifest.inputs`/`files`, 7 типов полей + FileUpload
- `components/job-stream/` — WebSocket live + EventFeed + ProgressBar
- `components/admin/` — AdminTable (TanStack), DrawerSheet (URL-state), 4 админ-таблицы
- `lib/api/` — client/server fetch helpers, types fallback, errors, ws helper
- `lib/auth/` — refresh, current-user (server-only)
- `lib/format.ts` — formatRelativeTime, formatDate, formatDuration, formatCurrency (RU locale)
