.PHONY: help install install-api install-worker install-sdk \
        test test-api test-worker test-sdk test-agents \
        lint lint-api lint-worker lint-sdk \
        fmt schema clean compose-up compose-down

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip

help:
	@echo "Команды (в монорепо mirea-agent-portal):"
	@echo "  install        — venv + editable install всех пакетов с dev-deps"
	@echo "  test           — все pytest-сюиты (api, worker, sdk, agents stubs)"
	@echo "  lint           — ruff на всём коде"
	@echo "  schema         — регенерация docs/manifest.schema.json"
	@echo "  compose-up     — docker compose up -d"
	@echo "  compose-down   — docker compose down -v"
	@echo "  clean          — удалить venv и временные кэши"

# --- Установка ---

install: $(VENV)/bin/python install-sdk install-api install-worker

$(VENV)/bin/python:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install-sdk:
	$(PIP) install -e "packages/portal-sdk-python[dev]"

install-api:
	$(PIP) install -e "apps/portal-api[dev]"

install-worker:
	$(PIP) install -e "apps/portal-worker[dev]"

# --- Тесты ---

test: test-sdk test-api test-worker test-agents

test-sdk:
	cd packages/portal-sdk-python && ../../$(VENV)/bin/pytest

test-api:
	cd apps/portal-api && ../../$(VENV)/bin/pytest

test-worker:
	cd apps/portal-worker && ../../$(VENV)/bin/pytest

test-agents:
	$(VENV)/bin/pytest agents/proverka_stub/tests agents/science_agent_stub/tests

# --- Линт ---

lint: lint-sdk lint-api lint-worker

lint-sdk:
	$(VENV)/bin/ruff check packages/portal-sdk-python

lint-api:
	$(VENV)/bin/ruff check apps/portal-api/portal_api

lint-worker:
	$(VENV)/bin/ruff check apps/portal-worker/portal_worker

fmt:
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

# --- Схема ---

schema:
	$(VENV)/bin/python packages/portal-sdk-python/scripts/gen_manifest_schema.py

# --- Compose ---

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v

# --- Чистка ---

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
