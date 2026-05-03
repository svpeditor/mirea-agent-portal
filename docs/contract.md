# Контракт агента — версия 0.1

Этот документ — единственный источник истины о том, как агент общается с порталом. Если код в `portal_sdk` расходится с этим документом — баг в коде, не в документе.

Целевая аудитория — студенты НУГ, которые пишут агенты для платформы.

---

## TL;DR

Агент — это любой исполняемый процесс, который:

1. Лежит в репозитории с `manifest.yaml` в корне
2. Читает параметры из `$PARAMS_FILE` (JSON)
3. Читает файлы пользователя из `$INPUT_DIR/<input_id>/...`
4. Пишет события прогресса в `stdout` (NDJSON, по строке на событие)
5. Кладёт результаты в `$OUTPUT_DIR/<filename>` (filename — из манифеста)
6. Завершает работу событием `result` (успех) или `failed` (неуспех)

Если ты пишешь агента на Python — используй `portal_sdk`. Он скрывает механику и даёт нормальный API: `agent.params`, `agent.progress(...)`, `agent.result(...)`. Дальше по тексту — детали для тех, кто пишет агента не на Python (Node.js, Go, что угодно).

---

## 1. `manifest.yaml`

[Полная Pydantic-схема в `packages/portal-sdk-python/portal_sdk/manifest.py`. Здесь — человеко-читаемая выжимка.]

### Корневые поля

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `id` | string | да | Уникальный slug, латиница и `-`. Попадает в URL, должен быть стабилен. |
| `name` | string | да | Название на русском, как видит пользователь. |
| `version` | string | да | Семвер, должен совпадать с git-тэгом. |
| `category` | string | да | Вкладка портала. Канонические значения, отрисованные в UI: `научная-работа`, `учебная`, `организационная`. SDK допускает кастомные строки на случай, если портал расширит набор вкладок — но до тех пор такой агент попадёт в общий список без выделенной вкладки. |
| `icon` | string | нет | Emoji или путь к PNG. По умолчанию первая буква `name`. |
| `short_description` | string | да | На плитке агента, до 200 символов. |
| `about` | string (markdown) | нет | Длинная страница «о агенте» в портале. |
| `inputs` | map | нет | Поля формы, см. ниже. |
| `files` | map | нет | Загрузка файлов и папок, см. ниже. |
| `outputs` | array | да | Возвращаемые артефакты. |
| `runtime` | object | да | Как запускать агента, см. ниже. |

### Поля формы — `inputs`

`inputs` — это словарь `{input_id: field_spec}`. Имя `input_id` попадает в `params` как ключ, поэтому используй латиницу.

Все типы полей имеют общие свойства: `label` (что видит пользователь), `help` (под полем мелким шрифтом), `required`.

| `type` | Дополнительно | Тип в `params` |
|---|---|---|
| `text` | `placeholder`, `default`, `min_length`, `max_length`, `pattern` | `str` |
| `textarea` | `placeholder`, `default`, `rows` | `str` |
| `number` | `default`, `min`, `max`, `step` | `float` |
| `checkbox` | `default` | `bool` |
| `select` | `options: [{value, label}]`, `default` | `str` |
| `radio` | `options: [{value, label}]`, `default` | `str` |
| `date` | `default` (ISO) | `str` (ISO-формат) |

### Файлы — `files`

`files` — словарь `{input_id: file_spec}`. Все типы поддерживают `accept` (список расширений), `max_total_size_mb`, `required`.

| `type` | Что грузит пользователь | Что видит агент |
|---|---|---|
| `single_file` | один файл | `$INPUT_DIR/<input_id>/<original_name>` |
| `multi_files` | пачка файлов | `$INPUT_DIR/<input_id>/file1, file2, ...` |
| `folder` | папка с подпапками целиком | `$INPUT_DIR/<input_id>/<original_structure>` |
| `zip` | один ZIP-архив | портал распаковывает: `$INPUT_DIR/<input_id>/<unzipped>` |

**Важно:** структура подпапок при `type: folder` сохраняется. Если пользователь загрузил папку с 46 подпапками-работами — агент увидит ровно 46 подпапок.

### Артефакты — `outputs`

`outputs` — массив. Каждый элемент:

```yaml
- id: report          # имя для использования в agent.result(...)
  type: docx          # docx|pdf|xlsx|zip|html|json|any
  label: "Заключение" # что видит пользователь над кнопкой скачать
  filename: "x.docx"  # как файл должен называться в $OUTPUT_DIR
  primary: true       # большая кнопка скачать (один на агента)
```

Портал после завершения проверяет, что все `filename` появились в `$OUTPUT_DIR`. Нет файла — job переводится в failed.

### Runtime

```yaml
runtime:
  docker:
    base_image: "python:3.12-slim"   # любой Python-образ
    setup:
      - "pip install -r requirements.txt"
    entrypoint: ["python", "agent.py"]

  llm:
    provider: openrouter             # пока единственный
    models:                          # whitelist моделей этого агента
      - "deepseek/deepseek-chat"     # дешёвая, доступна всем
      # claude/gpt — только если админ апрувнул при добавлении

  limits:
    max_runtime_minutes: 60          # хард-килл по таймауту
    max_memory_mb: 1024              # docker --memory
    max_cpu_cores: 2                 # docker --cpus
```

---

## 2. Runtime-протокол

### Что портал даёт агенту

| Канал | Содержимое |
|---|---|
| `$PARAMS_FILE` (env) | Путь к JSON с параметрами формы. Читать **один раз**. |
| `$INPUT_DIR` (env) | Путь к bind-mount. Внутри — подкаталог на каждое `files.<input_id>`. |
| `$OUTPUT_DIR` (env) | Путь к пустой bind-mount директории. Сюда писать артефакты. |
| `$OPENROUTER_API_KEY` (env) | Ключ для OpenRouter. **Уникальный на каждую задачу**, не реюзи. |
| `$OPENROUTER_BASE_URL` (env) | Эндпоинт прокси портала. Используй как `base_url` в OpenAI-клиенте. |

### Что агент пишет порталу

- `stdout` — построчный NDJSON. **Без буферизации**. Каждое событие — отдельная строка JSON.
- `stderr` — свободный текст. Складывается в логи задачи как есть. Сюда — `print()`, traceback, любой шум.
- Файлы — в `$OUTPUT_DIR/` с именами из `outputs[].filename`.

### События в stdout

Все события имеют поле `type`. Остальные поля зависят от типа.

#### `started`
Отправляется агентом сразу после старта. Если не отправлен в течение 30 секунд — портал считает, что агент завис.
```json
{"type":"started","ts":"2026-04-30T15:01:00Z"}
```

#### `progress`
Числовой прогресс 0..1 + опциональная подпись.
```json
{"type":"progress","value":0.42,"label":"Обработка 19 из 46"}
```

#### `log`
Сообщение пользователю в общую ленту. `level`: `debug` / `info` / `warn` / `error`.
```json
{"type":"log","level":"info","msg":"найдены файлы"}
```

#### `item_done`
Завершение одного элемента в серии (одной работы / статьи). Появляется в UI отдельной строкой со ✓.
```json
{"type":"item_done","id":"01","summary":"РЕКОМЕНДОВАНА","data":{"verdict":"approve","scientific":8.0}}
```
`data` — произвольный словарь. Портал собирает по нему сводку (например, гистограмму вердиктов).

#### `error`
Нефатальная ошибка. Агент **продолжает**.
```json
{"type":"error","id":"15","msg":"не найдена презентация","retryable":false}
```

#### `result` — финал успеха
```json
{"type":"result","artifacts":[{"id":"report","path":"экспертное_заключение.docx"},{"id":"summary","path":"summary.json"}]}
```
`path` — относительно `$OUTPUT_DIR`. `id` должен совпадать с `outputs[].id` из манифеста.

#### `failed` — финал неуспеха
```json
{"type":"failed","msg":"OpenRouter недоступен","details":"500 InternalServerError"}
```

### Правила

1. После `result` или `failed` агент **должен завершиться** (`exit 0` для result, любой код для failed).
2. Если процесс завершился без `result`/`failed` — портал считает агент failed с msg = «не отправил финальное событие».
3. Если процесс зависает дольше `max_runtime_minutes` — портал шлёт SIGTERM, через 10 сек SIGKILL.
4. Stdout буферизация: всегда `flush` после каждого события (`portal_sdk` это делает автоматически; на других языках — следи сам).

---

## 3. Python — через `portal_sdk`

### Установка

В Dockerfile агента:
```dockerfile
COPY packages/portal-sdk-python /sdk
RUN pip install /sdk
```

В `requirements.txt` агента:
```
portal-sdk
```

### API

```python
from portal_sdk import Agent

agent = Agent()                              # читает env, шлёт started
params = agent.params                        # dict
input_path = agent.input_dir("works_folder") # Path
output_path = agent.output_dir               # Path

agent.progress(0.5, "Half")                  # 0.0..1.0 + подпись
agent.log("info", "started processing")      # level: debug/info/warn/error
agent.item_done("01", summary="OK", data={"score": 8})
agent.error("02", "no presentation", retryable=False)

# Файлы агент пишет сам. SDK их не трогает.
(output_path / "report.docx").write_bytes(...)

agent.result(artifacts=[
    {"id": "report", "path": "report.docx"}
])
# или для остановки:
agent.failed("LLM не ответил", details="...")
```

После `result` / `failed` любой следующий вызов любого метода кидает `RuntimeError`.

### Локальная разработка без портала

```bash
portal-sdk-run-local agents/your-agent
```

Запросит параметры интерактивно, эмулирует bind-mount, покажет stdout агента.

---

## 4. Если агент не на Python

Контракт языконезависимый — нужно только следовать env-переменным и формату событий.

### Минимальный bash-агент

```bash
#!/bin/bash
PARAMS=$(cat "$PARAMS_FILE")
echo '{"type":"started","ts":"'$(date -u +%FT%TZ)'"}'
echo '{"type":"progress","value":0.5,"label":"halfway"}'
echo "Hello world" > "$OUTPUT_DIR/output.txt"
echo '{"type":"result","artifacts":[{"id":"out","path":"output.txt"}]}'
```

### Node.js
Просто пишешь `process.stdout.write(JSON.stringify({...}) + '\n')`. Всё.

### Любой язык
Точно так же. Главное — flush stdout после каждой строки.

---

## 5. Версионирование контракта

Текущая версия — **0.1**. Контракт версионируется отдельно от платформы. Любое breaking-изменение (удаление поля, переименование, изменение типа) — major bump (1.0 → 2.0). Совместимые добавления — minor (0.1 → 0.2).

Портал поддерживает все опубликованные версии контракта одновременно. Манифест может декларировать минимальную версию контракта:

```yaml
contract_version: "0.1"
```

(Это поле появится в 0.2 и далее. В 0.1 не нужно.)

---

## 6. Где задавать вопросы

- Issue в репозитории `mirea-agent-portal` с тэгом `contract`
- Канал команды агентов в Telegram (если есть)

---

## 7. LLM-прокси (с версии портала 1.2.4)

Если в `manifest.yaml` указан `runtime.llm`, портал даёт агенту доступ к OpenRouter
через свой прокси с pre-flight проверкой квоты.

### Что меняется в окружении агента

| env | Что |
|---|---|
| `OPENROUTER_API_KEY` | Ephemeral-ключ, уникальный на каждый job. Действует только пока job активен. |
| `OPENROUTER_BASE_URL` | URL прокси портала (`http://api:8000/llm/v1` в dev-стеке). Использовать как `base_url` в openai SDK. |

### Пример агента на Python

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ["OPENROUTER_BASE_URL"],
)

resp = client.chat.completions.create(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "Привет"}],
    max_tokens=200,         # ← важно! см. секцию ниже
)
```

### Поддерживаемые эндпоинты

- `POST /llm/v1/chat/completions` (включая `stream: true`)
- `POST /llm/v1/completions` (legacy)
- `GET /llm/v1/models` — возвращает только модели из вашего `runtime.llm.models`

Прочие OpenAI-эндпоинты (`embeddings`, `images`, `audio`, `files`, `fine-tuning`, `moderations`)
вернут `501 Not Implemented`.

### Whitelist моделей

В `manifest.yaml` укажите конкретные модели, которые агент будет использовать:

```yaml
runtime:
  llm:
    provider: openrouter
    models:
      - "deepseek/deepseek-chat"          # дешёвая, доступна всем
      - "anthropic/claude-haiku-4-5"      # требует апрува админа портала
```

Если в request body придёт модель не из этого списка — `403 model_not_in_whitelist`.

Глобальный whitelist моделей задаётся админом портала (env `LLM_ALLOWED_MODELS`).
Build agent_version упадёт с `model_not_allowed`, если в манифесте указана модель,
которой нет в глобальном whitelist'е.

### Квоты

- **Per-user в месяц:** дефолт `$5.0` USD. Reset 1-го числа каждого месяца в 00:00 МСК.
- **Per-job cap:** дефолт `$0.5` USD. Защищает от runaway-агента.
- При превышении — `402 quota_exhausted` или `402 per_job_cap_exceeded`.

Преподаватели/админы могут увеличить квоту индивидуальному юзеру через
`PATCH /api/admin/users/{id}/quota`.

### Важно: всегда указывайте `max_tokens`

Прокси делает pre-flight оценку стоимости запроса. Если `max_tokens` не указан,
прокси оценивает completion как "весь контекст модели" (worst case) — это может
зарезать запрос с 402 ещё до отправки в OpenRouter, даже если реальный ответ
был бы дешёвым.

Всегда указывайте `max_tokens` равным разумной верхней границе ответа.

### Error codes

| Код | HTTP | Когда |
|---|---|---|
| `invalid_ephemeral_token` | 401 | Bearer отсутствует / истёк / отозван |
| `quota_exhausted` | 402 | Месячная квота юзера исчерпана |
| `per_job_cap_exceeded` | 402 | На текущем job уже потрачено сверх cap |
| `model_not_in_whitelist` | 403 | Запрошенная модель не в `manifest.runtime.llm.models` |
| `not_implemented` | 501 | Эндпоинт не поддерживается прокси |
| `openrouter_upstream_error` | 502 | OpenRouter вернул 5xx |
| `openrouter_timeout` | 504 | OpenRouter не ответил за 30с |

Формат: `{"error": {"code": "...", "message": "..."}}`.

### Стриминг

`stream: true` в request body работает прозрачно. Прокси добавит
`stream_options.include_usage = true` чтобы посчитать стоимость, это никак не
влияет на формат стрима.

### Изоляция сети

Контейнер агента запускается в Docker-сети `portal-agents-net` с флагом
`internal: true`. Это означает: агент **физически не имеет выхода в интернет**,
кроме как до прокси портала. Любая попытка стучаться напрямую на
`https://openrouter.ai` или куда-либо ещё закончится timeout'ом на уровне сети.
