# Flaxon Framework Makefile
# Usage: make <target>

.PHONY: help install dev test lint type-check format clean build release docs serve

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Flaxon Framework Makefile$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install the package in development mode
	@echo "$(YELLOW)Installing Flaxon...$(NC)"
	python -m pip install -e ".[standard,dev]"
	@echo "$(GREEN)✓ Installation complete$(NC)"

dev: install ## Install development dependencies (alias for install)
	@echo "$(GREEN)✓ Development environment ready$(NC)"

test: ## Run the test suite
	@echo "$(YELLOW)Running tests...$(NC)"
	pytest -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	pytest --cov=flaxon --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated at htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "$(YELLOW)Running tests in watch mode...$(NC)"
	ptw

lint: ## Run linting
	@echo "$(YELLOW)Running linter...$(NC)"
	python scripts/check_lint_budget.py
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-fix: ## Run linter and fix issues
	@echo "$(YELLOW)Running linter with fixes...$(NC)"
	ruff check --fix .
	@echo "$(GREEN)✓ Linting fixes applied$(NC)"

type-check: ## Run type checking
	@echo "$(YELLOW)Running type checker...$(NC)"
	python scripts/typecheck.py
	@echo "$(GREEN)✓ Type checking complete$(NC)"

format: ## Format code with ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	ruff format .
	@echo "$(GREEN)✓ Code formatted$(NC)"

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .coverage.*
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf */*/__pycache__/
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

clean-all: clean ## Clean everything including virtual environment
	@echo "$(YELLOW)Cleaning everything...$(NC)"
	rm -rf .venv/
	rm -rf .tox/
	@echo "$(GREEN)✓ Clean complete$(NC)"

build: clean ## Build distribution packages
	@echo "$(YELLOW)Building distribution packages...$(NC)"
	python -m build
	@echo "$(GREEN)✓ Build complete$(NC)"
	@echo "$(BLUE)Packages created in dist/$(NC)"
	@ls -la dist/

release: build ## Build and prepare for release (alias for build)
	@echo "$(GREEN)✓ Ready for release$(NC)"

publish: build ## Build and publish to PyPI
	@echo "$(YELLOW)Publishing to PyPI...$(NC)"
	@echo "$(RED)⚠️  Make sure version is updated in __init__.py and CHANGELOG.md$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(YELLOW)❌ Aborted$(NC)"; \
	fi

docs: ## Build documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	cd docs && mkdocs build
	@echo "$(GREEN)✓ Documentation built in docs/_site/$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation...$(NC)"
	cd docs && mkdocs serve

pre-commit: ## Run all pre-commit checks
	@echo "$(YELLOW)Running all pre-commit checks...$(NC)"
	@$(MAKE) format
	@$(MAKE) lint
	@$(MAKE) type-check
	@$(MAKE) test
	@echo "$(GREEN)✓ All checks passed$(NC)"

check: lint type-check test ## Run all checks (alias for pre-commit)

docker-build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image...$(NC)"
	docker build -t flaxon:latest .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run Docker container
	@echo "$(YELLOW)Running Docker container...$(NC)"
	docker run --rm -p 8000:8000 -e FLAXON_ENV=production -e FLAXON_DEBUG=false flaxon:latest

tox: ## Run tests across multiple Python versions
	@echo "$(YELLOW)Running tox...$(NC)"
	tox
	@echo "$(GREEN)✓ Tox complete$(NC)"

benchmark: ## Run performance benchmarks
	@echo "$(YELLOW)Running benchmarks...$(NC)"
	python benchmarks/routing_benchmark.py
	python benchmarks/json_benchmark.py
	python benchmarks/middleware_benchmark.py
	@echo "$(GREEN)✓ Benchmarks complete$(NC)"

# Default target
.DEFAULT_GOAL := help