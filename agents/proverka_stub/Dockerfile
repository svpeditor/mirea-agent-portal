FROM python:3.12-slim

WORKDIR /agent

# Этот Dockerfile НЕ используется порталом для сборки proverka_stub при
# добавлении через POST /api/admin/agents — портал генерирует свой
# Dockerfile из manifest.yaml (см. apps/portal-worker/portal_worker/builder/
# dockerfile_gen.py), инжектит portal-sdk и собирает образ.
#
# Этот файл нужен только для local-dev: запустить агента вручную
# (`docker build -t proverka-stub .` + `docker run`). Для запуска без Docker
# (только через venv portal-sdk) — `portal-sdk-run-local`. См. README.md.

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py manifest.yaml ./

ENTRYPOINT ["python", "agent.py"]
