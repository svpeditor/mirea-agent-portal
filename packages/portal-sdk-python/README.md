# portal-sdk

Python-SDK для агентов платформы AI-агентов кафедры МИРЭА.

## Установка для разработки

```bash
cd packages/portal-sdk-python
python -m venv .venv
source .venv/bin/activate     # на Linux/macOS
# .venv\Scripts\activate       # на Windows
pip install -e ".[dev]"
```

## Быстрый старт

См. `agents/echo/agent.py` как минимальный пример.

```python
from portal_sdk import Agent

agent = Agent()
params = agent.params

agent.log("info", "started")
agent.progress(0.5, "halfway")

(agent.output_dir / "result.txt").write_text(params["message"])

agent.result(artifacts=[{"id": "report", "path": "result.txt"}])
```

## Локальный запуск без портала

```bash
portal-sdk-run-local agents/echo
```

Спросит параметры интерактивно, эмулирует bind-mount, покажет stdout агента.

## Тесты

```bash
pytest -v
```

## Полный контракт

`docs/contract.md` в корне моно-репо.

## Структура

| Файл | Что |
|---|---|
| `portal_sdk/manifest.py` | Pydantic-модели `manifest.yaml` |
| `portal_sdk/events.py` | NDJSON-события + `parse_event_line()` |
| `portal_sdk/agent.py` | Класс `Agent` — публичное API |
| `portal_sdk/local_runner.py` | CLI `portal-sdk-run-local` |
