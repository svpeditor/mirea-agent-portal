# Вопросы Дане

Открытые развилки, по которым autonomous-сессия не приняла решения сама. Удалить пункт после ответа.

## План 1.4 — milestone-1 (реальные агенты)

Stub'ы готовы (`agents/proverka_stub/`, `agents/science_agent_stub/`, см. ветку `feat/1.4-agents-stubs` и спек `docs/superpowers/specs/2026-05-10-1.4-agents-port-design.md`). Чтобы перейти к real:

1. **Где живут реальные репозитории `proverka` и `science_agent`?** Локальный путь или GitHub? Какое имя выбрать для публичных репо (на манер `mirea-agent-portal-echo-test`)?
2. **У real-`science_agent` — `deepseek-r1` через OpenRouter** (как в спеке/stub'е) или есть свой провайдер? Если OpenRouter — надо ли расширять `LLM_ALLOWED_MODELS` env у portal-worker?
3. **У real-`proverka` чек-лист научной экспертизы** — это живой artefact в репо (json/yaml) или хардкод в коде? От этого зависит структура `agents/proverka/` (отдельный файл `checklist.yaml` или нет).
4. **Есть ли state, который не должен попадать в публичный репо?** Ключи API, специфичные локальные пути, конфиги? Если есть — что прятать через env, что переносить отдельно.

## PR #6 (frontend 1.3)

Не self-merge'ил, как договаривались (cookie path change перерегистрирует существующие сессии). Жду твоего merge'а — после этого:
- Сделаю A3 (`requireAdmin` → `forbidden()` в `lib/auth/current-user.ts`).
- Подгоним frontend `lib/api/types.ts` под обновлённый openapi.json (`npm run codegen`).

## Backend backlog (PR #7-#10)

Все четыре PR открыты, тесты зелёные:
- #7 enrich JobListItemOut
- #8 outputs list endpoint
- #9 worker restart-on-failure
- #10 .gitignore .gstack/

Если хочешь — мерджи в любом порядке, конфликтов между ними нет (#7 и #8 trivial-mergeable друг с другом).
