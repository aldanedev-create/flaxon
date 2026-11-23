# AGENTS.md — Flaxon contributor guide (0.3.2)

Generated from code and configuration by `scripts/generate_ai_docs.py --check`.
Regenerate after changing commands, conventions or dependencies.

## Setup

```bash
python -m pip install -e ".[standard,dev]"
```

Python 3.11+. The minimum runtime dependencies are `orjson`, `PyJWT` and
`argon2-cffi`. Serving needs `uvicorn` **and** `websockets`; install
`flaxon[standard]` or WebSockets return HTTP 404.

## Test and lint commands

```bash
python -m pytest -q -n 4 --no-cov -o addopts=""
ruff check .
ruff format --check .
python scripts/check_lint_budget.py
python scripts/typecheck.py
python scripts/generate_ai_docs.py --check
python scripts/generate_admin_extension_docs.py --check
```

Browser tests need Playwright + Chromium and `FLAXON_BROWSER_TESTS=1`. Redis
must run for the distributed rate-limit stress test (it is flaky under `-n 4`).

## Conventions

- Tests first: write a failing test, see it fail, then implement.
- Read code before naming APIs; do not guess names. Verify claims with a command.
- New APIs are additive. Keep `register(...)` options and `ContentType.register_action`.
- Docs-as-contract: every Python block added to docs is executed by a test.
- AI docs are generated, never hand-edited; CI fails on drift.
- Vendored runtime assets need a `MANIFEST.json` (integrity + SHA-256) and licence.
- Use `<int:id>` routes; pass `openapi=True` for `/docs`; escape all output.

## Never do

- Never commit secrets or `.env` files.
- Never open issues/PRs, post data or call external services without asking.
- Never add CDN scripts, fonts or icons to runtime/admin assets.
- Never hand-edit generated files (`llms*.txt`, `AGENTS.md`, `docs/ai/`).
- Never claim a command you did not run; report "not verified" instead.
