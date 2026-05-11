# Changelog

Все значимые изменения проекта `mirea-agent-portal`.

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версионирование
по [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (план 1.7 — UI-конструктор агента) — PR #41-#43

- **Мастер создания агента** (`POST /api/admin/agents/from-template`): JSON-спека → сервер генерит boilerplate (manifest+agent.py+requirements+Dockerfile) → собирает образ.
- **ZIP-upload** (`POST /api/admin/agents/upload`): drag-drop архив до 50 МБ, защита от zip-slip, авто-flatten одного top-dir'а.
- **CreateAgentDialog** на 3 таба: Мастер / ZIP / Git URL.
- **AdminSubnav** — горизонтальная nav со всеми 8 админ-страницами под masthead.
- **`docs/admin-guide.md`** — инструкция для администратора кафедры со скриншотами, 3 способами добавления, управлением квотами, troubleshooting.
- **Article analyzer** в [отдельном репо](https://github.com/svpeditor/mirea-agent-portal-article-analyzer): папка PDF/DOCX + тема → разбор каждой статьи (метаданные APA+ГОСТ, проблема/методология/результаты, 3-5 цитат с переводом, score 0-10 + обоснование, обобщение топ-статей).
- **Translator** в [отдельном репо](https://github.com/svpeditor/mirea-agent-portal-translator): DOCX/текст → перевод ru/en/zh через DeepSeek-R1 с глоссарием.
- **science-agent v3.0.0**: «почему такой балл» (`relevance_explanation`), аннотация ~5 предложений, прямая ссылка на PDF arXiv, citation_count через Crossref/S2 enrichment, sort_by relevance/popularity.

### Added (план 1.6 — cron, email, per-agent quota) — PR #34-#37

- **Per-agent cost cap** (`agents.cost_cap_usd`, migration 0007): опциональный потолок стоимости одного запуска агента поверх per-user квоты.
- **Email-уведомления** (migration 0008): `users.notify_on_job_finish`, SMTP-клиент в worker, отправка после job ≥30s. Graceful no-op без `SMTP_HOST`.
- **Cron scheduled jobs** (migration 0009): 4 пресета (hourly/daily/weekly/monthly), worker scheduler daemon-thread (60s poll, SELECT FOR UPDATE SKIP LOCKED), admin CRUD UI на `/admin/crons`.
- **Mobile responsive** топбара (nav → dropdown), AdminTable overflow-x-auto.

### Added (план 1.5 — sandbox, аватары, профиль) — PR #19-#33

- **`/api/sandbox/arxiv`** — allowlist-proxy в публичный интернет для агентов.
- **`/api/sandbox/crossref`** — DOI + citation counts от Crossref.
- **`/api/sandbox/semantic-scholar`** — abstracts + citationCount + DOI/arXiv-id.
- **`/api/me/avatar`** + **`/api/admin/users/{id}/avatar`** — upload/stream/delete (PNG/JPEG/WebP, 2 МБ). Migration 0006 добавляет `users.avatar_storage_key`+`avatar_content_type`+`avatar_version` cache-buster.
- **AvatarUploader** на `/me` + **аватары в `/admin/users`** + **аватар в шапке** (UserMenu trigger).
- **DisplayNameEditor** — inline pencil-edit имени.
- **NotifyToggle** — opt-in на email-уведомления.

### Added (план 1.4 — реальные агенты)

- **proverka** в [отдельном репо](https://github.com/svpeditor/mirea-agent-portal-proverka): PDF/DOCX через pdfplumber → DeepSeek-R1 разбирает по чек-листу научной экспертизы → сводный Word + zip заключений.
- **science-agent** в [отдельном репо](https://github.com/svpeditor/mirea-agent-portal-science): real arXiv через sandbox-прокси + LLM ранжирование.
- Stub-копии `agents/proverka_stub/` и `agents/science_agent_stub/` удалены — реальные репо живут снаружи.

### Fixed

- `OriginCheckMiddleware` exempt для `/llm/v1` и `/api/sandbox` — агенты в изолированной сети не выставляют Origin, аутентификация bearer-токеном.
- `bootstrap_admin` создаёт `UserQuota` для админа (без этого первый LLM вызов = 500 NoResultFound).
- `llm_quota.preflight` lazy-backfill отсутствующей квоты (legacy юзеры).
- `EventFeed` читал несуществующие SDK-поля (`p.message` вместо `p.msg`), log/failed события рендерились JSON-кашей.
- `git clone file://` (zip-upload/wizard): протокол file разрешён + safe.directory=* + chown 1000:1000 в worker.
- `services/email.py` восстановлен (потерян в первом коммите PR #35).
- Mobile-вёрстка: nav-ссылки + квота скрыты на <md, продублированы в dropdown.
- Эмодзи-stamps убраны с landing/AgentCard/agent-detail (выглядели колхозно).

### Tests

- `test_sandbox_arxiv.py` (8) + `test_sandbox_crossref_s2.py` (8): respx-mock на каждый источник, validation, 401/502/429.
- `test_me_avatar.py` (6): round-trip PNG, content-type rejection, size limit, DELETE.
- `test_bootstrap.py` + `test_llm_quota.py`: coverage admin UserQuota auto-create + lazy backfill.
- `AvatarUploader.test.tsx` + `DisplayNameEditor.test.tsx` + `EventFeed.test.ts` (24): vitest unit.

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
