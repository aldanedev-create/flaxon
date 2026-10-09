# Contributing to Flaxon

Welcome! This document covers everything you need to know to contribute to Flaxon's core.

## Developer Setup

To get started contributing, you need:

- Python 3.9+
- Poetry 1.2+
- PostgreSQL 12+
- Redis 6+

Clone the repository and install dependencies:

```bash
git clone https://github.com/flaxon/framework.git
cd framework
poetry install
poetry run pre-commit install
```

## Running Tests

Run the full test suite with coverage:

```bash
poetry run pytest --cov=src --cov-report=html
```

Or run tests for a specific module:

```bash
poetry run pytest tests/test_middleware_security.py -v
```

## Code Style

We use several linting tools to maintain consistency:

- **Ruff**: For fast linting and import sorting
- **mypy**: Static type checking
- **black**: Code formatting (handled by Ruff)

Run linters manually:

```bash
python scripts/check_lint_budget.py
poetry run ruff format src/
python scripts/typecheck.py
```

The lint budget prevents increases by file and rule; `ruff check src/flaxon`
still reports all legacy findings. Do not expand the budget to hide new debt.
The typing command checks 11 core modules without following unchecked imports.
Use `python scripts/typecheck.py --full` for the wider audit, which currently
reports existing failures. [Quality audit and measurements](quality-audit.md).

## Debugging Issues

If you encounter test failures:

1. Check the test output for database connection errors
2. Ensure Redis is running locally
3. Verify environment variables in `.env`

For more detailed debugging, enable verbose logging:

```bash
poetry run python -m pytest --log-cli-level=DEBUG tests/
```
