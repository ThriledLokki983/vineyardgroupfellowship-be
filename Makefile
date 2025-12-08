# Makefile for Vineyard Group Fellowship Django Backend
# ===================================================
#
# This Makefile provides commands for both local development and Docker-based development
#
# Prerequisites:
# - Docker and Docker Compose installed
# - direnv installed and configured (optional)
# - Python virtual environment (for local development)
#
# Usage:
#   make help          # Show available commands
#   make local-dev     # Start local development with PostgreSQL
#   make infra-up      # Start infrastructure services
#   make status        # Show service status

# ============================================================================
# CONFIGURATION
# ============================================================================

# Local development (if using virtual environment)
VENV=/Users/gnimoh001/Desktop/vineyard-group-fellowship/backend/.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

# Docker configuration
PROJECT_NAME=vineyard-group-fellowship
DOCKER_COMPOSE=docker compose --project-name $(PROJECT_NAME)
DOCKER_COMPOSE_DEV=$(DOCKER_COMPOSE) -f docker-compose.yml
DOCKER_COMPOSE_DEV=$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.override.yml
DOCKER_COMPOSE_PROD=$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml

# Service names
WEB_SERVICE=web
DB_SERVICE=postgres
REDIS_SERVICE=redis
MAILHOG_SERVICE=mailhog

# Colors for output
BLUE=\033[34m
GREEN=\033[32m
YELLOW=\033[33m
RED=\033[31m
NC=\033[0m # No Color

.DEFAULT_GOAL := help
.PHONY: help dev dev-build dev-rebuild dev-up dev-down dev-logs dev-shell dev-restart dev-clean \
        infrastructure infra-up infra-down infra-logs \
        test test-dev \
        migrate migrate-dev \
        superuser superuser-dev \
        check check-dev \
        fmt lint \
        clean clean-all \
        setup setup-local \
        status \
        local-dev local-migrate local-superuser local-check local-deploycheck \
        local-test local-setup local-setup-dev local-fmt local-shell local-makemigrations \
        local-showmigrations

# ============================================================================
# HELP & INFORMATION
# ============================================================================

help: ## Show this help message
	@echo "$(BLUE)Vineyard Group Fellowship Django Backend - Development Commands$(NC)"
	@echo "=============================================================="
	@echo ""
	@echo "$(GREEN)🐍 Local Development Commands (Recommended):$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^local-[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)🐳 Docker Development Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^dev.*:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)🧪 Testing & Quality Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && (/test/ || /check/ || /fmt/ || /lint/) && !/local/ && !/dev/ {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)🛠️  Infrastructure Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && (/infra/ || /clean/ || /setup/) {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)📊 Monitoring Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && (/status/ || /logs/) {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BLUE)Quick Start (Local Development):$(NC)"
	@echo "  1. make local-setup       # Install dependencies"
	@echo "  2. make local-migrate     # Setup database"
	@echo "  3. make local-dev         # Start development server"
	@echo "  4. make local-superuser   # Create admin user"

# ============================================================================
# DEVELOPMENT ENVIRONMENT (DOCKER)
# ============================================================================

dev: dev-down dev-build dev-up ## Start complete development environment with file watching
	@echo "$(GREEN)🚀 Development environment started!$(NC)"
	@echo "$(BLUE)Application: http://localhost:8002$(NC)"
	@echo "$(BLUE)Admin: http://localhost:8002/admin/$(NC)"
	@echo "$(BLUE)Health: http://localhost:8002/health/$(NC)"
	@echo "$(BLUE)MailHog UI: http://localhost:8025$(NC)"
	@echo ""
	@echo "$(YELLOW)Use 'make dev-logs' to view logs$(NC)"
	@echo "$(YELLOW)Use 'make dev-shell' to open a shell$(NC)"

dev-build: ## Build development services
	@echo "$(BLUE)🔨 Building development services...$(NC)"
	@$(DOCKER_COMPOSE) build

dev-rebuild: ## Rebuild development services with no cache
	@echo "$(BLUE)🔨 Rebuilding development services (no cache)...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache

dev-up: ## Start development services in background
	@echo "$(BLUE)⬆️  Starting development services...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Services started!$(NC)"
	@make status

dev-up-attach: ## Start development services with logs attached
	@echo "$(BLUE)⬆️  Starting development services with logs...$(NC)"
	@$(DOCKER_COMPOSE) up

dev-down: ## Stop development services
	@echo "$(BLUE)⬇️  Stopping development services...$(NC)"
	@$(DOCKER_COMPOSE) down

dev-restart: dev-down dev-up ## Restart development services
	@echo "$(GREEN)🔄 Development services restarted!$(NC)"

dev-logs: ## View development logs (follow)
	$(DOCKER_COMPOSE_DEV) logs -f $(DEV_SERVICE)

dev-shell: ## Open shell in web container
	@$(DOCKER_COMPOSE) exec $(WEB_SERVICE) /bin/bash

dev-clean: ## Clean development environment
	@echo "$(BLUE)🧹 Cleaning development environment...$(NC)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans


# ============================================================================
# PRODUCTION TESTING
# ============================================================================

prod: prod-build prod-up ## Start production testing environment
	@echo "$(GREEN)🚀 Production testing environment started!$(NC)"
	@echo "$(BLUE)Application: http://localhost:8001$(NC)"
	@echo "$(YELLOW)Note: HTTPS redirects enabled (use internal checks)$(NC)"

prod-build: ## Build production Docker image
	@echo "$(BLUE)🔨 Building production image...$(NC)"
	$(DOCKER_COMPOSE_PROD) build $(PROD_SERVICE)

prod-up: ## Start production testing services
	@echo "$(BLUE)🚀 Starting production services...$(NC)"
	$(DOCKER_COMPOSE_PROD) up -d $(PROD_SERVICE)

prod-down: ## Stop production testing services
	@echo "$(BLUE)🛑 Stopping production services...$(NC)"
	$(DOCKER_COMPOSE_PROD) down

prod-logs: ## View production logs
	$(DOCKER_COMPOSE_PROD) logs -f $(PROD_SERVICE)

prod-shell: ## Open shell in production container
	$(DOCKER_COMPOSE_PROD) exec $(PROD_SERVICE) bash

# ============================================================================
# INFRASTRUCTURE MANAGEMENT
# ============================================================================

infra-up: ## Start infrastructure services only (PostgreSQL, Redis, MailHog)
	@echo "$(GREEN)🔧 Starting infrastructure services...$(NC)"
	@./infra-start.sh

infra-down: ## Stop infrastructure services
	@echo "$(BLUE)🛑 Stopping infrastructure services...$(NC)"
	$(DOCKER_COMPOSE) stop $(DB_SERVICE) $(REDIS_SERVICE) $(MAILHOG_SERVICE)

infra-restart: ## Restart infrastructure services
	@echo "$(BLUE)� Restarting infrastructure services...$(NC)"
	$(DOCKER_COMPOSE) restart $(DB_SERVICE) $(REDIS_SERVICE) $(MAILHOG_SERVICE)

infra-logs: ## View infrastructure logs
	$(DOCKER_COMPOSE) logs -f $(DB_SERVICE) $(REDIS_SERVICE) $(MAILHOG_SERVICE)

infra-clean: ## Clean infrastructure data (WARNING: destroys data)
	@echo "$(RED)⚠️  This will destroy all data! Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	@echo "$(BLUE)🧹 Cleaning infrastructure data...$(NC)"
	$(DOCKER_COMPOSE) down -v $(DB_SERVICE) $(REDIS_SERVICE) $(MAILHOG_SERVICE)

# ============================================================================
# DATABASE & MIGRATIONS (DOCKER)
# ============================================================================

migrate-dev: ## Run migrations in Docker development
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) /app/venv/bin/python manage.py migrate

superuser-dev: ## Create superuser in Docker development
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) /app/venv/bin/python manage.py createsuperuser

# ============================================================================
# TESTING & QUALITY (DOCKER)
# ============================================================================

test-dev: ## Run tests in Docker development environment
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) python -m pytest -v

check-dev: ## Run Django system checks (Docker development)
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) python manage.py check

fmt: ## Format code with ruff and black
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) ruff check --select I --fix .
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) ruff format .

lint: ## Lint code with ruff
	$(DOCKER_COMPOSE_DEV) exec $(WEB_SERVICE) ruff check .

# ============================================================================
# LOCAL DEVELOPMENT (Virtual Environment + PostgreSQL Infrastructure)
# ============================================================================

local-dev: ## Start Django development server (local Python with PostgreSQL)
	@echo "$(GREEN)🐍 Starting Django development server with PostgreSQL...$(NC)"
	@echo "$(YELLOW)Infrastructure services must be running (make infra-up)$(NC)"
	@echo "$(BLUE)Ensuring infrastructure is running...$(NC)"
	@$(DOCKER_COMPOSE) up -d $(DB_SERVICE) $(REDIS_SERVICE) $(MAILHOG_SERVICE) || echo "$(YELLOW)Infrastructure already running$(NC)"
	@echo "$(GREEN)Starting Django development server on port $${SERVER_PORT:-8001}...$(NC)"
	$(PYTHON) manage.py runserver 0.0.0.0:$${SERVER_PORT:-8001}

local-migrate: ## Apply database migrations (local Python to PostgreSQL)
	@echo "$(GREEN)🔄 Applying database migrations...$(NC)"
	@echo "$(BLUE)Ensuring PostgreSQL is running...$(NC)"
	@$(DOCKER_COMPOSE) up -d $(DB_SERVICE) || echo "$(YELLOW)PostgreSQL already running$(NC)"
	@echo "$(GREEN)Running migrations...$(NC)"
	$(PYTHON) manage.py migrate

local-superuser: ## Create Django superuser (local Python to PostgreSQL)
	@echo "$(GREEN)👤 Creating Django superuser...$(NC)"
	@echo "$(BLUE)Ensuring PostgreSQL is running...$(NC)"
	@$(DOCKER_COMPOSE) up -d $(DB_SERVICE) || echo "$(YELLOW)PostgreSQL already running$(NC)"
	@echo "$(GREEN)Creating superuser...$(NC)"
	$(PYTHON) manage.py createsuperuser

local-check: ## Run Django system checks (local Python)
	@echo "$(GREEN)✅ Running Django system checks...$(NC)"
	$(PYTHON) manage.py check

local-deploycheck: ## Run production deployment checks (local Python)
	@echo "$(GREEN)🚀 Running deployment checks...$(NC)"
	$(PYTHON) manage.py check --deploy

local-test: ## Run test suite (local Python)
	@echo "$(GREEN)🧪 Running test suite...$(NC)"
	$(PYTHON) manage.py test

local-setup: ## Install Python dependencies (local Python)
	@echo "$(GREEN)📦 Installing Python dependencies...$(NC)"
	$(PIP) install -r requirements.txt

local-setup-dev: ## Install development dependencies (local Python)
	@echo "$(GREEN)📦 Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt

local-fmt: ## Format code (local Python)
	@echo "$(GREEN)🎨 Formatting code...$(NC)"
	@$(PYTHON) -m ruff format . || echo "$(YELLOW)Ruff not installed, skipping format$(NC)"
	@$(PYTHON) -m black . || echo "$(YELLOW)Black not installed, skipping format$(NC)"

local-shell: ## Open Django shell (local Python with PostgreSQL)
	@echo "$(GREEN)🐚 Opening Django shell...$(NC)"
	@echo "$(BLUE)Ensuring PostgreSQL is running...$(NC)"
	@$(DOCKER_COMPOSE) up -d $(DB_SERVICE)
	@echo "$(GREEN)Opening shell...$(NC)"
	$(PYTHON) manage.py shell

local-makemigrations: ## Create new migrations (local Python)
	@echo "$(GREEN)📝 Creating new migrations...$(NC)"
	$(PYTHON) manage.py makemigrations

local-showmigrations: ## Show migration status (local Python)
	@echo "$(GREEN)📋 Showing migration status...$(NC)"
	@echo "$(BLUE)Ensuring PostgreSQL is running...$(NC)"
	@$(DOCKER_COMPOSE) up -d $(DB_SERVICE)
	@echo "$(GREEN)Checking migrations...$(NC)"
	$(PYTHON) manage.py showmigrations

# ============================================================================
# MONITORING & STATUS
# ============================================================================

status: ## Show status of all services
	@echo "$(BLUE)📊 Service Status:$(NC)"
	$(DOCKER_COMPOSE) ps

logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs --tail=50 -f

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Clean development environment
	@echo "$(YELLOW)🧹 Cleaning development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) down --remove-orphans
	@echo "$(GREEN)Cleaning Python cache files...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

clean-all: ## Clean everything (containers, volumes, images)
	@echo "$(RED)⚠️  WARNING: This will remove all containers, volumes, and images!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)🧹 Cleaning everything...$(NC)"; \
		$(DOCKER_COMPOSE) down -v --rmi all --remove-orphans; \
	else \
		echo "$(GREEN)✅ Cancelled.$(NC)"; \
	fi

# ============================================================================
# LEGACY ALIASES (for backward compatibility)
# ============================================================================

setup: local-setup ## Alias for local-setup
install: local-setup ## Alias for local-setup
run: local-dev ## Alias for local-dev
migrate: local-migrate ## Alias for local-migrate
makemigrations: local-makemigrations ## Alias for local-makemigrations
superuser: local-superuser ## Alias for local-superuser
shell: local-shell ## Alias for local-shell
test: local-test ## Alias for local-test
check: local-check ## Alias for local-check
deploycheck: local-deploycheck ## Alias for local-deploycheck