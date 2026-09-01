.PHONY: help setup install backend-install frontend-install backend-run frontend-run dev test lint format clean docker-up docker-down

# Default target
help:
	@echo "LossGraph Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup              - Setup entire project"
	@echo "  make install            - Install all dependencies"
	@echo "  make backend-install    - Install backend dependencies"
	@echo "  make frontend-install   - Install frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make backend-run        - Run backend server"
	@echo "  make frontend-run       - Run frontend dev server"
	@echo "  make dev                - Run backend and frontend (requires two terminals)"
	@echo ""
	@echo "Testing:"
	@echo "  make test               - Run all tests"
	@echo "  make backend-test       - Run backend tests"
	@echo "  make frontend-test      - Run frontend tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint               - Lint all code"
	@echo "  make backend-lint       - Lint backend code"
	@echo "  make frontend-lint      - Lint frontend code"
	@echo "  make format             - Format all code"
	@echo "  make backend-format     - Format backend code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up          - Start all services with Docker"
	@echo "  make docker-down        - Stop all Docker services"
	@echo "  make docker-logs        - View Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              - Clean build artifacts and cache"
	@echo "  make clean-db           - Clean database"
	@echo ""

# Setup entire project
setup:
	@echo "🚀 Setting up LossGraph..."
	@bash setup.sh

# Install all dependencies
install: backend-install frontend-install

# Backend setup
backend-install:
	@echo "📦 Installing backend dependencies..."
	@cd backend && \
	python3 -m venv venv && \
	. venv/bin/activate && \
	pip install -r requirements.txt && \
	echo "✓ Backend dependencies installed"

# Frontend setup
frontend-install:
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && \
	npm install && \
	echo "✓ Frontend dependencies installed"

# Run backend
backend-run:
	@echo "🚀 Starting backend server..."
	@cd backend && \
	. venv/bin/activate && \
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend
frontend-run:
	@echo "🎨 Starting frontend dev server..."
	@cd frontend && \
	npm run dev

# Run both (development)
dev:
	@echo "🚀 Starting LossGraph development servers..."
	@echo "⚠️  Run this in one terminal, or open two separate terminals"
	@echo ""
	@echo "Backend (Terminal 1):"
	@echo "  cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload"
	@echo ""
	@echo "Frontend (Terminal 2):"
	@echo "  cd frontend && npm run dev"
	@echo ""
	@echo "Then open: http://localhost:3000"

# Testing
test: backend-test frontend-test

backend-test:
	@echo "🧪 Running backend tests..."
	@cd backend && \
	. venv/bin/activate && \
	pytest -v

frontend-test:
	@echo "🧪 Running frontend tests..."
	@cd frontend && \
	npm test

# Linting
lint: backend-lint frontend-lint

backend-lint:
	@echo "✓ Linting backend code..."
	@cd backend && \
	. venv/bin/activate && \
	flake8 app/ && \
	isort --check app/ && \
	black --check app/

frontend-lint:
	@echo "✓ Linting frontend code..."
	@cd frontend && \
	npm run lint

# Code formatting
format: backend-format

backend-format:
	@echo "📝 Formatting backend code..."
	@cd backend && \
	. venv/bin/activate && \
	isort app/ && \
	black app/

# Docker commands
docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d
	@echo "✓ Services started!"
	@echo ""
	@echo "URLs:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Database: localhost:5432"

docker-down:
	@echo "🐳 Stopping Docker services..."
	docker-compose down

docker-logs:
	docker-compose logs -f

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✓ Cleanup complete"

clean-db:
	@echo "🗑️  Cleaning database..."
	@rm -f backend/lossgraph.db
	@echo "✓ Database cleaned"

# Database
db-init:
	@echo "📊 Initializing database..."
	@cd backend && \
	. venv/bin/activate && \
	python -c "from app.database import init_db; init_db(); print('✓ Database initialized')"

db-reset: clean-db db-init
	@echo "✓ Database reset complete"

# Generate synthetic data
generate-data:
	@echo "📊 Generating synthetic test data..."
	@python3 -m data.generation.generate --scale demo --seed 42
	@echo "✓ Data generation complete"

# Full offline intelligence pipeline: synthetic data -> three engines ->
# fusion -> loss events -> counterfactual simulation -> LLM investigator ->
# chargeback responder. Run this before starting the backend -- it serves
# these precomputed artifacts, it does not recompute them per request (see
# backend/app/data_access.py). Set ANTHROPIC_API_KEY for real LLM
# narratives/drafts; without it, both LLM steps fall back to deterministic
# templates automatically (PRD section 43 failure handling).
pipeline: generate-data
	@echo "🧠 Running intelligence pipeline..."
	@python3 -m ml.risk_model
	@python3 -m ml.graph_engine
	@python3 -m ml.anomaly_engine
	@python3 -m ml.fusion
	@python3 -m ml.loss_events
	@python3 -m ml.counterfactual
	@python3 -m ml.investigator
	@python3 -m ml.chargeback_responder
	@echo "✓ Pipeline complete -- ml/artifacts/loss_events_with_policy.json ready"

# Build production images
docker-build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✓ Build complete"

# Push to registry (requires configuration)
docker-push:
	@echo "📤 Pushing to registry..."
	docker-compose push
	@echo "✓ Push complete"
