FROM python:3.12-slim

WORKDIR /agent

# Этот Dockerfile НЕ используется порталом для сборки echo при добавлении
# через POST /api/admin/agents. Портал генерирует свой Dockerfile из
# manifest.yaml (см. apps/portal-worker/portal_worker/builder/dockerfile_gen.py),
# инжектит portal-sdk и собирает образ как portal/agent-echo:v<sha7>.
#
# Этот файл нужен только для local-dev: запустить агента вручную через
# Docker без портала (`docker build -t echo-local .` + `docker run`).
# Для запуска агента БЕЗ Docker (используя только venv portal-sdk) есть
# CLI portal-sdk-run-local — см. agents/echo/README.md.
COPY requirements.txt ./
RUN pip install --no-cache-dir python-docx

COPY agent.py manifest.yaml ./

ENTRYPOINT ["python", "agent.py"]
