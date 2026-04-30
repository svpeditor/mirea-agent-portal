FROM python:3.12-slim

WORKDIR /agent

# Зависимости самого echo. portal-sdk сюда НЕ ставится из PyPI —
# его нет на PyPI. Портал в Спеке 1.2 будет собирать образ агента
# с инжекцией pip install /sdk поверх этого Dockerfile (build context
# портала добавляет packages/portal-sdk-python в образ как /sdk).
# Для локальной разработки используется portal-sdk-run-local через
# venv пакета (см. agents/echo/README.md), без Docker вовсе.
COPY requirements.txt ./
RUN pip install --no-cache-dir python-docx

COPY agent.py manifest.yaml ./

ENTRYPOINT ["python", "agent.py"]
