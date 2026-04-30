FROM python:3.12-slim

WORKDIR /agent

# SDK поставится отдельно через docker build context портала.
# Здесь зависимости самого echo:
COPY requirements.txt ./
RUN pip install --no-cache-dir python-docx

COPY agent.py manifest.yaml ./

ENTRYPOINT ["python", "agent.py"]
