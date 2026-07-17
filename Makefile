# Makefile — entry-point for the advanced-rag project.
# Wraps the app stack (docker-compose.yml), the infra stack (infra/), and
# local backend/frontend workflows. Run `make` or `make help` for the list.

# Use bash and fail fast.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

COMPOSE := docker compose
INFRA_COMPOSE := docker compose -f infra/docker-compose.yml

.DEFAULT_GOAL := help

# ── Help ────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@echo "Usage: make <target>"
	@echo
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Environment ─────────────────────────────────────────────────────────────
.PHONY: env
env: .env infra/.env ## Create .env files from .env.example (skips existing)

.env:
	cp .env.example .env
	@echo ">> created .env — fill in FPT_API_KEY + model IDs before running the app"

infra/.env:
	cp infra/.env.example infra/.env
	@echo ">> created infra/.env"

# ── App stack (Qdrant + backend + frontend) ─────────────────────────────────
.PHONY: up
up: .env ## Build & start the full app stack (Qdrant + backend + frontend)
	$(COMPOSE) up --build

.PHONY: up-d
up-d: .env ## Start the app stack in the background
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop the app stack
	$(COMPOSE) down

.PHONY: logs
logs: ## Tail app stack logs
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show app stack container status
	$(COMPOSE) ps

# ── Infra stack (MLflow + RustFS + Postgres) ────────────────────────────────
.PHONY: infra-up
infra-up: infra/.env ## Build & start the infra stack (MLflow + RustFS + Postgres)
	$(INFRA_COMPOSE) up --build

.PHONY: infra-up-d
infra-up-d: infra/.env ## Start the infra stack in the background
	$(INFRA_COMPOSE) up --build -d

.PHONY: infra-down
infra-down: ## Stop the infra stack
	$(INFRA_COMPOSE) down

.PHONY: infra-logs
infra-logs: ## Tail infra stack logs
	$(INFRA_COMPOSE) logs -f

# ── Backend (local, no Docker) ──────────────────────────────────────────────
.PHONY: backend-install
backend-install: ## Install backend Python deps
	cd backend && pip install -r requirements.txt

.PHONY: backend-dev
backend-dev: ## Run the backend locally with reload (needs .env)
	cd backend && uvicorn app.main:app --reload

.PHONY: test
test: ## Run backend offline unit tests
	cd backend && pytest

# ── Frontend (local, no Docker) ─────────────────────────────────────────────
.PHONY: frontend-install
frontend-install: ## Install frontend npm deps
	cd frontend && npm install

.PHONY: frontend-dev
frontend-dev: ## Run the Vite dev server
	cd frontend && npm run dev

.PHONY: frontend-build
frontend-build: ## Typecheck + build the frontend (tsc -b && vite build)
	cd frontend && npm run build

# ── Cleanup ─────────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Stop both stacks and remove their volumes (destroys data)
	$(COMPOSE) down -v
	$(INFRA_COMPOSE) down -v
