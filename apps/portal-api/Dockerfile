FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY packages/portal-sdk-python /portal-sdk-src

COPY apps/portal-api/pyproject.toml ./
RUN sed -i 's#file:../../packages/portal-sdk-python#file:///portal-sdk-src#' pyproject.toml && \
    pip install --no-cache-dir -e ".[dev]"

COPY apps/portal-api/ .

COPY apps/portal-api/scripts/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000
CMD ["/start.sh"]
