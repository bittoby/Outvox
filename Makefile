# Outvox developer task runner.
#
# Creates a single `.venv` at the repo root and installs both the backend
# requirements and the test requirements into it. The .venv is the single
# Python execution environment for every backend task.
#
# Run `make help` for the full task list. Windows contributors: see dev.ps1
# for an equivalent runner.

.PHONY: help install install-be install-fe install-tests test test-be lint typecheck \
        build dev-be dev-fe clean

# Python launcher. Override on the command line if you need a specific
# version, e.g. `make install PYTHON=python3.12`. The minimum supported
# version is 3.11. Maximum is whatever has wheels for pydantic_core and
# asyncpg (3.13 at the time of writing).
PYTHON ?= python3
NPM    ?= npm

VENV       := .venv
VENV_PY    := $(VENV)/bin/python
VENV_PIP   := $(VENV_PY) -m pip

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*##"; printf "Outvox tasks:\n"} \
	      /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)

$(VENV_PY):
	@echo ">> creating .venv with $(PYTHON)"
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip --quiet

install: install-be install-tests install-fe ## Install backend, test and frontend dependencies.

install-be: $(VENV_PY) ## Install backend Python dependencies into .venv.
	$(VENV_PIP) install -r BE/requirements.txt

install-tests: $(VENV_PY) ## Install test dependencies into .venv.
	$(VENV_PIP) install -r tests/requirements.txt

install-fe: ## Install frontend npm dependencies.
	cd FE && $(NPM) ci

test: test-be ## Run all automated tests (currently backend pytest only).

test-be: ## Run the backend pytest suite via .venv.
	$(VENV_PY) -m pytest

lint: ## Lint frontend code.
	cd FE && $(NPM) run lint

typecheck: ## Type-check frontend code.
	cd FE && npx tsc -b --noEmit

build: ## Build the frontend for production.
	cd FE && $(NPM) run build

dev-be: ## Run the database service locally (port 8000).
	cd BE && ../$(VENV_PY) db_service.py

dev-fe: ## Run the frontend dev server (port 3000).
	cd FE && $(NPM) run dev

clean: ## Remove build and cache artifacts (including .venv).
	rm -rf FE/dist FE/node_modules/.cache .pytest_cache $(VENV)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
