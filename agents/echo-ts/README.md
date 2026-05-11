# echo-ts

TypeScript-эквивалент `agents/echo/` (Python). Доказывает что TS SDK работает 1:1 с Python SDK на контракте порталa.

Использует `@mirea/portal-sdk` + `docx` npm-пакет для генерации Word.

## Запуск локально

```bash
cd agents/echo-ts
npm install
mkdir -p /tmp/echo-ts-output
echo '{"message":"привет","loops":3,"shout":false}' > /tmp/echo-ts-params.json
PARAMS_FILE=/tmp/echo-ts-params.json \
INPUT_DIR=/tmp/echo-ts-input \
OUTPUT_DIR=/tmp/echo-ts-output \
node agent.js
ls /tmp/echo-ts-output/  # echo.docx + summary.json
```

## Публикация

Аналогично echo-агенту (Python) — отдельный git-репо + POST /api/admin/agents.
