# Contributing to Flaxon

Thank you for your interest in contributing to Flaxon! 🎉

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Report a Bug

1. Check if the bug is already reported in [Issues](https://github.com/aldanedev-create/Flaxon-Backend-Framework/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python version, Flaxon version)

### Suggest a Feature

1. Check if the feature is already requested
2. Create a feature request with:
   - Clear description of the feature
   - Why it's valuable
   - Potential implementation approach

### Submit Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes with tests
4. **Run the full test suite** (see below) and confirm it passes -- a partial
   or single-file test run is not sufficient before opening a PR
5. Run linting: `python scripts/check_lint_budget.py`
6. Run type checking: `python scripts/typecheck.py`
7. Commit with clear messages
8. Push and open a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/aldanedev-create/Flaxon-Backend-Framework.git
cd Flaxon-Backend-Framework

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all extras
pip install -e ".[standard,dev]"

# Install browser test dependencies (see "Running the full test suite" below)
pip install playwright pytest-playwright
python -m playwright install chromium
```

## Running the Full Test Suite

Before opening a pull request, contributors must run the **full** test suite,
not just the tests touching their own change -- a change that looks isolated
can still break something elsewhere (route matching, admin/CMS wiring, and
the CLI have all had regressions from changes that looked unrelated).

The project's `pytest.ini` already configures coverage reporting, strict
markers, and test discovery across the whole `tests/` directory, so running
the suite is just:

```bash
pytest
```

This includes `tests/browser/`, which drives a real Chromium browser via
Playwright -- make sure you've run `python -m playwright install chromium`
first (see Development Setup above), or those tests will fail rather than
being skipped.

Useful variations while iterating locally:

```bash
# Fast pass while developing, without coverage overhead
pytest --no-cov

# A single test file or directory
pytest tests/integration/test_router_specificity.py -v --no-cov

# Skip browser tests if you don't have a display/Chromium available locally
pytest --ignore=tests/browser
```

None of the shortcuts above are a substitute for a full `pytest` run before
submitting a PR -- CI (and reviewers) will run the complete suite regardless.

## Code Style

- Follow PEP 8
- Use type hints for all function signatures
- Write docstrings for public APIs
- Keep functions focused and small
- Prefer async/await for I/O operations

## Linting Configuration

Flaxon uses Ruff for linting and formatting. Configuration is in `ruff.toml`;
use the pinned development version so the legacy budget is reproducible.
`python scripts/check_lint_budget.py` rejects increases for every file/rule pair.
`ruff check src/flaxon` reports the full remaining debt. Reduce the checked-in
baseline when fixing old findings; do not increase it to accept new warnings.

## Type Checking

Flaxon uses mypy for static type checking. Configuration is in `mypy.ini`.
`python scripts/typecheck.py` checks 11 core modules with the strict configuration.
Imports from unchecked modules are not followed by this gate. Run
`python scripts/typecheck.py --full` to audit the whole package; that command
currently fails on existing typing debt. See [the audit](docs/quality-audit.md).

## Test Organization

- Unit tests in `tests/unit/` -- test individual components
- Integration tests in `tests/integration/` -- test component interactions
- Security tests in `tests/security/` -- test security properties
- Performance tests in `tests/performance/` -- benchmark performance
- Browser tests in `tests/browser/` -- real end-to-end tests via Playwright

## Writing Tests

```python
# tests/unit/test_example.py
from flaxon import Flaxon
from flaxon.testing.client import AsyncTestClient

async def test_route():
    app = Flaxon("test")

    @app.get("/")
    async def home():
        return {"message": "hello"}

    response = await AsyncTestClient(app).request("GET", "/")
    assert response.status_code == 200
```

## Pull Request Process

1. Update `CHANGELOG.md` with your changes
2. Update documentation if necessary
3. Ensure the full test suite passes (`pytest`, not a partial run)
4. Get at least one maintainer review
5. Squash commits before merging

## Release Process

1. Update version in `src/flaxon/version.py`
2. Update `CHANGELOG.md`
3. Tag the release: `git tag v0.2.4`
4. Push tags: `git push --tags`
5. GitHub Actions will build and publish to PyPI

## Maintainers

Aldane Hutchinson (@aldane)

## Questions?

- Open an issue for bugs or feature requests
- Join our Discord for community support
- Email: aldanehutchinson5@gmail.com

Thank you for contributing to Flaxon! 🚀