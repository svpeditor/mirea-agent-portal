# portal-sdk

Python-SDK для агентов платформы AI-агентов кафедры МИРЭА.

## Установка

```bash
pip install -e ./packages/portal-sdk-python
```

Или через `uv`:

```bash
uv pip install -e ./packages/portal-sdk-python
```

## Быстрый старт

```python
from portal_sdk import Agent

agent = Agent()
params = agent.params
input_dir = agent.input_dir("my_input")
output_dir = agent.output_dir

agent.log("info", "Начинаю обработку")
agent.progress(0.5, "Половина пути")
agent.result(artifacts=["report"])
```

## Локальный запуск агента без портала

```bash
portal-sdk-run-local agents/echo
```

Полный контракт — в `docs/contract.md` корня репо.
