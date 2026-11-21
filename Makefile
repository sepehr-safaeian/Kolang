.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Meta ──────────────────────────────────────────────────────────────────────
.PHONY: help install fmt lint test test-cov test-unit test-integration test-e2e \
        security migrate migrate-new dev up down clean ci docs all

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────
install: ## Install project with dev dependencies and pre-commit hooks
	pip install -e ".[dev]"
	pre-commit install

# ── Formatting & Linting ─────────────────────────────────────────────────────
fmt: ## Auto-format code with ruff
	ruff format .
	ruff check --fix .

lint: ## Run linters (ruff + mypy)
	ruff check .
	ruff format --check .
	mypy packages/

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run all tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

test-e2e: ## Run end-to-end tests only
	pytest tests/e2e/

# ── Security ──────────────────────────────────────────────────────────────────
security: ## Run security checks with bandit
	bandit -r packages/ -c pyproject.toml

# ── Database ──────────────────────────────────────────────────────────────────
migrate: ## Apply all pending database migrations
	alembic upgrade head

migrate-new: ## Create a new auto-generated migration
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# ── Development ───────────────────────────────────────────────────────────────
dev: ## Start the development server with hot-reload
	uvicorn apps.api.app.main:app --reload --host 0.0.0.0 --port 8000

# ── Docker ────────────────────────────────────────────────────────────────────
up: ## Start all services with Docker Compose
	docker compose -f deploy/docker-compose.yml up -d --build

down: ## Stop all Docker Compose services
	docker compose -f deploy/docker-compose.yml down

# ── Housekeeping ──────────────────────────────────────────────────────────────
clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info

# ── CI Pipeline (local) ──────────────────────────────────────────────────────
ci: lint test-cov security ## Run the full CI pipeline locally

# ── Docs ──────────────────────────────────────────────────────────────────────
docs: ## Build documentation (placeholder)
	@echo "📚 Documentation build not yet configured. See docs/ directory."

# ── All ───────────────────────────────────────────────────────────────────────
all: install lint test-cov security ## Full setup: install, lint, test, security scan
