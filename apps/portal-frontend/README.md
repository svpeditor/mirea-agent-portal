# portal-frontend

Next.js 15 frontend для портала НУГ.

## Local dev

```bash
cp .env.example .env
npm install
npm run dev
```

Открой http://localhost:3000.

## Tests

- `npm run lint` — ESLint + tsc
- `npm test` — Vitest unit
- `npm run test:e2e` — Playwright e2e (требует docker compose up для backend)

## Codegen API types

```bash
npm run codegen
```

Регенерирует `lib/api/types.ts` из `http://localhost:8000/openapi.json`.

## Build

```bash
npm run build
npm start
```

Через Docker — см. `docker-compose.yml` сервис `frontend`.
