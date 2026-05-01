FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 999 docker && \
    useradd --create-home --shell /bin/bash --uid 1000 worker && \
    usermod -aG docker worker
COPY --chown=worker:worker packages/portal-sdk-python /portal-sdk-src
COPY --chown=worker:worker apps/portal-worker/pyproject.toml ./
RUN sed -i 's#file:../../packages/portal-sdk-python#file:///portal-sdk-src#' pyproject.toml && \
    pip install --no-cache-dir -e "."
COPY --chown=worker:worker apps/portal-worker/portal_worker /app/portal_worker
USER worker
CMD ["python", "-m", "portal_worker.main"]
