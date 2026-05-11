# Changelog

Все значимые изменения проекта `mirea-agent-portal`.

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версионирование
по [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (план 1.4 — реальные агенты)

- **proverka** в [отдельном репо](https://github.com/svpeditor/mirea-agent-portal-proverka): PDF/DOCX через pdfplumber → DeepSeek-R1 разбирает по чек-листу научной экспертизы → сводный Word + zip заключений.
- **science-agent** в [отдельном репо](https://github.com/svpeditor/mirea-agent-portal-science) v2.0.0: real arXiv search через `/api/sandbox/arxiv` + LLM ранжирование, fallback на LLM-knowledge режим.
- Stub-копии `agents/proverka_stub/` и `agents/science_agent_stub/` удалены — реальные репо живут снаружи и подключаются через `POST /api/admin/agents`.

### Added (план 1.5 — sandbox, аватары, профиль)

- **`/api/sandbox/arxiv`** — allowlist-proxy для агентов в публичный интернет. Bearer ephemeral-token auth, Atom-feed arXiv → JSON, Origin middleware exempt.
- **`/api/me/avatar`** + **`/api/admin/users/{id}/avatar`** — POST upload (PNG/JPEG/WebP, 2 МБ), GET stream, DELETE. Migration 0006 добавляет `users.avatar_storage_key` + `avatar_content_type`.
- **`UserOut.has_avatar` + `avatar_version`** — короткий cache-buster для img URL.
- **`AvatarUploader`** на `/me` со stamp-превью + Заменить/Удалить.
- **`DisplayNameEditor`** — inline pencil-edit для display_name.
- **Аватары в `/admin/users`** — колонка с stamp в UsersTable.
- **Аватар в шапке** — `<img>` вместо initial-буквы в UserMenu trigger.

### Fixed (план 1.5)

- `OriginCheckMiddleware` exempt для `/llm/v1` и `/api/sandbox` — агенты в изолированной сети не выставляют Origin, аутентификация bearer-токеном.
- `bootstrap_admin` создаёт `UserQuota` для админа (без этого первый LLM вызов = 500 NoResultFound).
- `llm_quota.preflight` lazy-backfill отсутствующей квоты (legacy юзеры из preview-БД).
- `EventFeed` читал несуществующие SDK-поля (`p.message` вместо `p.msg`), из-за чего log/failed события рендерились как JSON-каша.

### Tests (план 1.5)

- `test_sandbox_arxiv.py` (8): respx-mock на Atom-feed, validation, 401/502 ответы.
- `test_me_avatar.py` (6): round-trip PNG, content-type rejection, size limit, DELETE flow.
- `test_bootstrap.py` + `test_llm_quota.py`: coverage admin UserQuota auto-create + lazy backfill.
- `AvatarUploader.test.tsx` + `DisplayNameEditor.test.tsx` (11): vitest unit.
- `EventFeed.test.ts` (7): фиксирует SDK→UI контракт (msg/id/summary).

---

## [план 1.3 — merged 2026-05-11, PR #6]

### Added (frontend)

- **Frontend Next.js 15** — план 1.3, 12 страниц в editorial-вёрстке «Известия НУГ».
- **Cmd+K command palette** — поиск страниц и быстрые переходы (Notion/Linear-style).
- **/admin/audit** — журнал админ-действий с фильтром по типу ресурса.
- **/admin/system** — дашборд статуса системы (ping postgres+redis + uptime).
- **Cancel button** на `/jobs/{id}` — для queued/running с двухшаговым confirm.
- **Drag-and-drop FileUpload** + folder-walk через webkitGetAsEntry.
- **Cursor-pagination** на `/jobs` (30/стр) + фильтр-чипы по статусу.
- **Editorial skeleton loading** вместо «Загрузка…».
- **Auto-refresh** /jobs если есть queued/running (5с polling, document.hidden-aware).
- **JobsTable** — имя агента + стоимость; `JobOutputs` widget с download-кнопками.
- **UsersTable** — колонки «Лимит», «LLM, $», «Запросов» из агрегата `/admin/usage`.
- **Динамический landing** — каталог из `/api/public/catalog`.
- **CreateAgentDialog** на `/admin/agents` — git_url + git_ref form.
- **forbidden() миграция** — 403 рендерится через `app/forbidden.tsx`.

### Added (backend)

- **`/api/public/catalog`** — публичный endpoint для landing (без auth).
- **`/api/health/full`** — readiness probe с ping postgres+redis.
- **`/api/admin/audit`** — журнал действий (cursor pagination, фильтры).
- **`/api/jobs/{id}/outputs`** — list endpoint для output-файлов.
- **JobListItemOut enrichment** — agent_slug, agent_name, cost_usd_total через join.
- **Login rate limit** 5/15min sliding window через Redis (per ip+email).
- **Admin audit log** — таблица `admin_audit_log` + integration в invite/user/tab/agent/version/quota роуты.
- **Sentry integration** (api + worker) — opt-in через `SENTRY_DSN`.
- **ws_token cookie** — non-httpOnly дубль access_token для cross-port WebSocket handshake.
- **WS auth ?token= fallback** — для случаев когда cookies не доходят.

### Added (DX/CI)

- **TypeScript SDK skeleton** — `@mirea/portal-sdk`, 1:1 эквивалент Python-SDK.
- **`docs/agent-developer-guide.md`** — пошаговый гид для студентов НУГ.
- **`docs/manifest.schema.json`** — JSON Schema для IDE-автокомплита.
- **`portal-sdk-validate-manifest`** CLI.
- **GitHub Actions CI** — 4 job (sdk/api/worker/agents).
- **Makefile** — install/test/lint/schema/compose-up.
- **`scripts/backup-db.sh`** + **`restore-db.sh`** + **`docs/deploy-guide.md`**.

### Added (агенты)

- **`agents/proverka_stub/`** — folder-input → docx report + zip per-work.
- **`agents/science_agent_stub/`** — textarea topic → docx + bibtex, runtime.llm объявлен.
- **`agents/echo-ts/`** — TypeScript-эквивалент echo, доказывает 1:1 совместимость TS SDK с контрактом портала.
- Опубликованы в каталоге: `svpeditor/mirea-agent-portal-{proverka,science}-stub`.

### Added (admin)

- **`GET /api/admin/jobs`** + **`/admin/jobs`** UI — все запуски всех юзеров с пагинацией и авто-обновлением.
- **`POST /api/admin/audit/cleanup`** — ручной cleanup старых audit-записей (минимум 30 дней).

### Fixed

- **EventFeed `Invalid time value`** — useJobWebSocket пихал `{type:"resync"}` как JobEvent. Теперь resync-сообщение распаковывается отдельно.
- **WS 403 cross-port** — cookies не доходили на :8000 от :3000. Добавлен `ws_token` cookie без httpOnly + query-fallback.
- **`since=undefined`** в WS URL — `String(undefined)`. Сейчас фильтруется.
- **RQ 2.x positional args** — `Extra positional arguments cannot be used with kwargs`. Пакуем payload в dict.
- **`shutil.copy2` vs directory** — folder-input ломался. Switch на `copytree`.
- **`/var/portal-files/{job_id}` perms** — api как root, worker uid 1000, нет write. `chmod 0o777` на mkdir.
- **`LLM_AGENTS_NETWORK_NAME`** — `portal-agents-net` ≠ compose-namespaced `agent_portal-wave0_portal-agents-net`.
- **Logout form submission canceled** — `<form action=POST>` в Radix DropdownMenu отменялся при close. Заменили на client-side fetch + `router.push`.
- **Worker restart race** — `recover_orphaned_builds` падал до миграций. Добавлен `restart: on-failure:3`.

### Changed

- **Cookie `path=/api` → `/`**, `samesite=strict` → `lax` — нужен для cross-port WS и frontend rewrite на корне.
- **Landing** — был статикой с mock-агентами, теперь live из API.

## [0.2.0] — 2026-05-03

### Added

- **План 1.2.4** — LLM-прокси OpenRouter + per-user/per-job квоты + ephemeral-токены + internal docker network + admin endpoints (PR #5).

## [0.1.0] — 2026-04-30

### Added

- **SDK v0.1.0** — Контракт + Python-SDK + echo-агент (PR #1, tag `sdk-v0.1.0`).
- **Backend 1.2.1** — FastAPI skeleton + auth (PR #2).
- **Backend 1.2.2** — Реестр агентов (tabs/agents/agent_versions) + Git-clone + Docker build (PR #3).
- **Backend 1.2.3** — Jobs/worker/Docker-runner/WebSocket (PR #4).
