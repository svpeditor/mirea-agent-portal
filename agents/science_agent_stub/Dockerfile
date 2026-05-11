FROM python:3.12-slim

WORKDIR /agent

# Этот Dockerfile НЕ используется порталом для сборки science_agent_stub
# при добавлении через POST /api/admin/agents — портал генерирует свой
# Dockerfile из manifest.yaml. См. README.md.

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py manifest.yaml ./

ENTRYPOINT ["python", "agent.py"]
