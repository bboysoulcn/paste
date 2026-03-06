.PHONY: help install test lint build up down restart logs migrate

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -e ".[dev]"

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=app --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint: ## Run linting
	ruff check .
	mypy app/ --ignore-missing-imports || true

lint-fix: ## Fix linting issues automatically
	ruff check . --fix

build: ## Build Docker image
	docker build -t paste .

up: ## Start all services with docker-compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

logs-paste: ## Show logs from paste service
	docker-compose logs -f paste

migrate: ## Run database migrations
	docker-compose exec paste alembic upgrade head

migrate-create: ## Create a new migration (use MSG="description")
	docker-compose exec paste alembic revision --autogenerate -m "$(MSG)"

migrate-local: ## Run migrations locally
	alembic upgrade head

clean: ## Clean up build artifacts
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -delete
	find . -type f -name '*.pyc' -delete

dev: ## Run development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

prod: ## Run production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
