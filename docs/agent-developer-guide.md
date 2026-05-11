# Гид разработчика агента

Эта страница для студентов НУГ, которые пишут собственного агента под платформу.

Для админов портала и для подробного описания контракта — `docs/contract.md`.

## Что такое агент

Агент платформы — это **отдельный исполняемый процесс**, который:
- получает параметры формы и пользовательские файлы из переменных окружения,
- пишет события прогресса в stdout (по строке JSON на событие),
- кладёт результаты-файлы в указанную папку и завершает работу событием `result` или `failed`.

Платформа берёт твой git-репозиторий, читает `manifest.yaml` в корне, собирает Docker-образ и сама поднимает контейнер на каждый запуск задачи.

## Как написать агента — пошагово

### 1. Поставь SDK

```bash
git clone https://github.com/<твой_логин>/<имя-агента>.git
cd <имя-агента>
python -m venv .venv && source .venv/bin/activate
pip install "git+https://github.com/svpeditor/mirea-agent-portal.git#subdirectory=packages/portal-sdk-python"
```

Или если ты внутри monorepo `mirea-agent-portal`:

```bash
pip install -e packages/portal-sdk-python
```

После установки доступны две CLI-команды:
- `portal-sdk-run-local <agent_dir>` — запустить агента локально без портала.
- `portal-sdk-validate-manifest <agent_dir>` — проверить `manifest.yaml`.

### 2. Скопируй reference-агента

Самый простой шаблон — `agents/echo/` в монорепо:

```
агент/
├── manifest.yaml      # паспорт агента
├── agent.py           # основной код
├── requirements.txt   # зависимости pip
├── Dockerfile         # для local-dev (портал собирает свой)
└── README.md
```

### 3. Опиши `manifest.yaml`

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/svpeditor/mirea-agent-portal/main/docs/manifest.schema.json

id: my-agent              # uniq slug, латиница и -
name: "Мой агент"         # как видит препод
version: "0.1.0"          # семвер
category: "научная-работа"  # одна из вкладок портала
icon: "🧪"
short_description: |
  Что делает агент в одной фразе.

inputs:                    # поля формы
  topic:
    type: textarea
    label: "Тема"
    required: true

files:                     # загрузка файлов (опционально)
  works:
    type: folder
    label: "Папка с работами"
    accept: [".pdf", ".docx"]

outputs:                   # что вернёт агент
  - id: report
    type: docx
    label: "Отчёт"
    filename: "report.docx"
    primary: true

runtime:
  docker:
    base_image: "python:3.12-slim"
    setup:
      - "pip install -r requirements.txt"
    entrypoint: ["python", "agent.py"]
  limits:
    max_runtime_minutes: 30
    max_memory_mb: 512
    max_cpu_cores: 1
```

Подсказка по полям и типам — `docs/contract.md`. JSON Schema для IDE-автокомплита — `docs/manifest.schema.json`.

Проверь манифест:

```bash
portal-sdk-validate-manifest .
```

### 4. Напиши `agent.py`

```python
from portal_sdk import Agent

def main() -> None:
    agent = Agent()
    topic = agent.params["topic"]

    # Если есть files: works в манифесте — путь к папке:
    # works_dir = agent.input_dir("works")
    # for work in works_dir.iterdir(): ...

    agent.log("info", f"Получена тема: {topic}")
    n = 5
    for i in range(n):
        agent.progress((i + 1) / n, f"Шаг {i + 1} из {n}")
        agent.item_done(f"step-{i + 1}", summary="готово")

    # Запиши файлы в agent.output_dir
    (agent.output_dir / "report.docx").write_bytes(b"...")  # реальный docx через python-docx

    agent.result(artifacts=[{"id": "report", "path": "report.docx"}])

if __name__ == "__main__":
    main()
```

API класса `Agent`:

| Метод / поле | Что делает |
|---|---|
| `agent.params` | `dict` параметров формы |
| `agent.input_dir(input_id)` | `Path` к папке с пользовательскими файлами |
| `agent.output_dir` | `Path`, куда писать артефакты |
| `agent.env` | read-only view на `os.environ` |
| `agent.progress(value, label)` | значение 0..1 + подпись |
| `agent.log(level, msg)` | `info` / `warn` / `error` / `debug` |
| `agent.item_done(id, summary, data)` | завершён один из N элементов |
| `agent.error(msg, item_id, retryable)` | нефатальная ошибка по элементу |
| `agent.result(artifacts)` | финальный успех + файлы |
| `agent.failed(msg, details)` | финальная ошибка |

### 5. Запусти локально

```bash
mkdir -p _local_output
portal-sdk-run-local . --output-dir _local_output
```

CLI спросит параметры в интерактиве и эмулирует то, что портал делает в проде: готовит `$PARAMS_FILE`, `$INPUT_DIR`, `$OUTPUT_DIR`, читает stdout NDJSON, складывает результаты в `_local_output/`.

Альтернатива — вручную через env:

```bash
mkdir -p /tmp/agent-input /tmp/agent-output
echo '{"topic":"my topic"}' > /tmp/agent-params.json
PARAMS_FILE=/tmp/agent-params.json \
INPUT_DIR=/tmp/agent-input \
OUTPUT_DIR=/tmp/agent-output \
python agent.py
```

### 6. Покрой тестами

Минимум — валидация манифеста (он не сломается случайной правкой):

```python
# tests/test_manifest.py
from pathlib import Path
from portal_sdk.manifest import Manifest

def test_manifest_parses() -> None:
    m = Manifest.from_yaml(Path(__file__).parent.parent / "manifest.yaml")
    assert m.id == "my-agent"
```

Запуск:

```bash
pytest tests/
```

### 7. Запушь и опубликуй

```bash
git add . && git commit -m "init my-agent" && git push
```

Сообщи админу платформы, что хочешь добавить агента. Он сделает:

```bash
curl -X POST http://<портал>/api/admin/agents \
  -H "Content-Type: application/json" \
  -d '{"git_url": "https://github.com/<ты>/my-agent.git", "git_ref": "main"}'
```

Портал клонирует репо, валидирует манифест, собирает Docker-образ и публикует агента в каталоге.

## Доступ к LLM

Если агент использует LLM — добавь в манифест:

```yaml
runtime:
  llm:
    provider: openrouter
    models:
      - "deepseek/deepseek-r1"
      - "anthropic/claude-haiku-4-5-20251001"
```

Платформа проксирует OpenRouter и сама управляет квотами на пользователя. В env агента появится `OPENROUTER_API_KEY` (одноразовый ephemeral-токен на этот запуск) и `OPENROUTER_BASE_URL`. Агент вызывает любой OpenAI-совместимый клиент:

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ["OPENROUTER_BASE_URL"],
)

resp = client.chat.completions.create(
    model="anthropic/claude-haiku-4-5-20251001",
    messages=[{"role": "user", "content": "..."}],
)
```

Стоимость каждого запроса учитывается в квоте пользователя автоматически. Использовать модели вне `runtime.llm.models` нельзя — прокси отдаст ошибку.

## Чек-лист перед публикацией

- [ ] `portal-sdk-validate-manifest .` проходит
- [ ] Локальный запуск `portal-sdk-run-local .` отрабатывает на типовом вводе
- [ ] `pytest tests/` зелёный
- [ ] `manifest.yaml` содержит `# yaml-language-server: $schema=...` строку
- [ ] `README.md` объясняет, что агент делает и какие у него inputs/outputs
- [ ] `requirements.txt` зафиксирован (без свободных диапазонов >=)
- [ ] `agent.py` обрабатывает пустой ввод и пишет `agent.failed(...)` вместо краша

## Когда что-то идёт не так

| Симптом | Что проверить |
|---|---|
| `portal-sdk-validate-manifest` ругается на поле | смотри `docs/contract.md` для типа поля + JSON Schema |
| Агент падает локально с `KeyError: 'PARAMS_FILE'` | используй `portal-sdk-run-local`, не `python agent.py` напрямую |
| Портал собирает образ и падает на `pip install` | в `requirements.txt` версии могут конфликтовать с base_image — пини точные |
| `agent.result(...)` бросает `FileNotFoundError` | артефакт не записан в `output_dir` до вызова `result` |
| Стрим прогресса в UI заморожен | проверь, что `agent.progress(...)` зовётся регулярно (не реже раза в N минут) |
| LLM 401 | модель не в `runtime.llm.models` либо квота пользователя исчерпана |

## Ссылки

- `docs/contract.md` — полный контракт
- `docs/manifest.schema.json` — JSON Schema для IDE
- `agents/echo/` — reference-агент в монорепо
- `agents/proverka_stub/`, `agents/science_agent_stub/` — два примера разных форматов inputs

Если нашёл расхождение между этим гидом и реальным поведением — открой issue, гид важнее не привирать.
