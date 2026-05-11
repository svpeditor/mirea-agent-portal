# @mirea/portal-sdk

TypeScript SDK для агентов платформы AI-агентов МИРЭА.

1:1 эквивалент Python-SDK (`portal-sdk-python`). Контракт событий идентичен — агенты на TS и Python видны порталу одинаково.

## Установка

```bash
npm install @mirea/portal-sdk
# или из git
npm install git+https://github.com/svpeditor/mirea-agent-portal.git#subdirectory=packages/portal-sdk-ts
```

## Использование

```typescript
import { Agent } from '@mirea/portal-sdk';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

const agent = new Agent();
const topic = String(agent.params.topic ?? '(не указано)');

agent.log('info', `Тема: ${topic}`);

const N = 5;
for (let i = 0; i < N; i++) {
  agent.progress((i + 1) / N, `Шаг ${i + 1} из ${N}`);
  agent.itemDone(`step-${i + 1}`, `готово ${i + 1}`);
}

// Запиши файлы в agent.outputDir
writeFileSync(join(agent.outputDir, 'report.txt'), `Тема: ${topic}\n`);

agent.result([{ id: 'report', path: 'report.txt' }]);
```

## API

| Метод / поле | Что делает |
|---|---|
| `new Agent()` | Читает PARAMS_FILE/INPUT_DIR/OUTPUT_DIR из env, эмитит `started` |
| `agent.params` | `Record<string, unknown>` параметров формы |
| `agent.inputDir(id)` | путь к папке с пользовательскими файлами |
| `agent.outputDir` | путь куда писать артефакты |
| `agent.progress(value, label?)` | 0..1 + опциональная подпись |
| `agent.log(level, msg)` | `debug` / `info` / `warn` / `error` |
| `agent.itemDone(id, summary?, data?)` | завершён один из N элементов |
| `agent.error(msg, itemId?, retryable?)` | нефатальная ошибка по элементу |
| `agent.result(artifacts)` | финальный успех + файлы |
| `agent.failed(msg, details?)` | финальная ошибка |

## Манифест

`manifest.yaml` остаётся таким же. В `runtime.docker.entrypoint` указывай команду Node:

```yaml
runtime:
  docker:
    base_image: "node:20-alpine"
    setup:
      - "npm ci --omit=dev"
    entrypoint: ["node", "agent.js"]
```

См. полный гид в `docs/agent-developer-guide.md`.

## Тесты

```bash
npm install
npm test
```

## Что не реализовано (vs Python)

- CLI `portal-sdk-run-local` — используй Python-версию для локального запуска (env shared).
- `portal-sdk-validate-manifest` — Python-версия универсальна (читает yaml через Pydantic).
