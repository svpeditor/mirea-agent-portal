# science_agent_stub

Stub-агент под контракт SDK v0.1 (План 1.4, milestone-0).

Имитирует работу `science_agent`: возвращает фиксированный mock-набор статей по теме, формирует Word-отчёт и BibTeX. Дополнительно — smoke-test 1.2.4: логирует наличие `OPENROUTER_API_KEY` в env, чтобы проверить что ephemeral-токен пробрасывается до контейнера агента (но сам LLM пока не вызывает).

Real-версия живёт в локальном репо Дани и подтянется в milestone-1 (см. `docs/superpowers/plans/2026-05-10-1.4-agents-port.md`).

## Запуск без Docker

```bash
pip install -e packages/portal-sdk-python python-docx
mkdir -p /tmp/sci_input /tmp/sci_output
echo '{"topic":"machine learning медицина","max_papers":5,"language":"en"}' > /tmp/sci_params.json

INPUT_DIR=/tmp/sci_input \
OUTPUT_DIR=/tmp/sci_output \
PARAMS_FILE=/tmp/sci_params.json \
python agents/science_agent_stub/agent.py
```

## Манифест и LLM

Манифест объявляет `runtime.llm.models = [deepseek/deepseek-r1, anthropic/claude-haiku-4-5-20251001]`. Это значит: при создании job через портал backend выпускает ephemeral-токен и кладёт `OPENROUTER_API_KEY` в env агентского контейнера. Stub-агент его только логирует (не звонит OpenRouter), real-версия будет полноценно использовать прокси `/llm/v1/chat/completions`.
