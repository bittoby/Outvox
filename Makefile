# Outvox developer task runner.
#
# Targets are intentionally thin wrappers around the commands documented in
# README.md so the README stays the source of truth. Run `make help` for the
# list. Windows contributors: see dev.ps1 for an equivalent runner.

.PHONY: help install install-be install-fe install-tests test test-be lint typecheck \
        build dev-be dev-fe clean

PYTHON ?= python
NPM ?= npm

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*##"; printf "Outvox tasks:\n"} \
	      /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)

install: install-be install-fe install-tests ## Install BE, FE and test dependencies.

install-be: ## Install backend Python dependencies.
	$(PYTHON) -m pip install -r BE/requirements.txt

install-fe: ## Install frontend npm dependencies.
	cd FE && $(NPM) ci

install-tests: ## Install backend test dependencies.
	$(PYTHON) -m pip install -r tests/requirements.txt python-dotenv

test: test-be ## Run all automated tests (currently backend pytest only).

test-be: ## Run the backend pytest suite.
	$(PYTHON) -m pytest

lint: ## Lint frontend code.
	cd FE && $(NPM) run lint

typecheck: ## Type-check frontend code.
	cd FE && npx tsc -b --noEmit

build: ## Build the frontend for production.
	cd FE && $(NPM) run build

dev-be: ## Run the database service locally (port 8000).
	cd BE && $(PYTHON) db_service.py

dev-fe: ## Run the frontend dev server (port 3000).
	cd FE && $(NPM) run dev

clean: ## Remove build and cache artifacts.
	rm -rf FE/dist FE/node_modules/.cache .pytest_cache .venv-test
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
