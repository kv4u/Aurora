# ═══════════════════════════════════════════════
#  AURORA — Trading System Commands
# ═══════════════════════════════════════════════

.PHONY: help up down restart logs backend-logs frontend-logs db-logs
.PHONY: migrate migrate-create seed test test-backend test-e2e
.PHONY: install lint format health shell

# ─── Help ───
help: ## Show this help
	@echo ""
	@echo "  AURORA Trading System"
	@echo "  ════════════════════"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ─── Docker ───
up: ## Start all services
	docker compose up -d
	@echo "\n  AURORA is starting..."
	@echo "  Dashboard: http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs\n"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

build: ## Rebuild all containers
	docker compose build --no-cache

# ─── Logs ───
logs: ## Show all service logs
	docker compose logs -f --tail=50

backend-logs: ## Show backend logs
	docker compose logs -f --tail=50 backend

frontend-logs: ## Show frontend logs
	docker compose logs -f --tail=50 frontend

db-logs: ## Show database logs
	docker compose logs -f --tail=50 postgres

# ─── Database ───
migrate: ## Run database migrations
	docker compose exec backend alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed historical market data
	docker compose exec backend python -m scripts.seed_historical_data

# ─── Testing ───
test: test-backend test-e2e ## Run all tests

test-backend: ## Run backend unit tests
	docker compose exec backend pytest -v --cov=app --cov-report=term-missing

test-e2e: ## Run Playwright E2E tests
	cd tests/e2e && npx playwright test

# ─── Development ───
install: ## Install all dependencies locally
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
	cd tests/e2e && npm install

lint: ## Run linters
	cd backend && ruff check .
	cd frontend && npm run lint

format: ## Format code
	cd backend && ruff format .

# ─── Utilities ───
health: ## Check system health
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "Backend not running"

shell: ## Open backend shell
	docker compose exec backend python -c "from app.config import get_settings; print('AURORA shell ready')"

clean: ## Clean up volumes and containers
	docker compose down -v
	@echo "Cleaned up all AURORA containers and volumes"
