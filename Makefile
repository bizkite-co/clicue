#!/usr/bin/env bash
.PHONY: help
help: ## Display this help screen
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[32m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==============================================================================
# Application Tasks
# ==============================================================================

.PHONY: lint
lint: ## Run code linters (ruff & mypy)
	uv run ruff check .
	uv run mypy src

.PHONY: test
test: ## Run all unit tests
	uv run python3 -m unittest discover tests

.PHONY: check
check: lint test ## Run all linters and tests

.PHONY: hooks
hooks: ## Configure git pre-commit hook
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	@echo "✅ Git hooks configured to use .githooks/"
