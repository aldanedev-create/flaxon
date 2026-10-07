# Expanded behavioral tests

This suite adds 100 test modules and 514 collected test cases. Each module
covers a behavior or boundary of the real framework. Tests exercise HTTP
responses, persistence, authorization, malformed input, expiration, and
concurrency; they contain no placeholders, expected failures, or skipped cases.

| Area | Test modules | Cases |
| --- | ---: | ---: |
| Validation fields and schemas | 20 | 141 |
| HTTP routing, requests, responses, and streams | 15 | 73 |
| Admin authentication, permissions, CMS, and durable state | 15 | 71 |
| Security middleware, credentials, CSRF, and rate limits | 10 | 69 |
| Files, SQLite transactions, and migrations | 10 | 41 |
| Caching, session lifecycle, signatures, and serialization | 10 | 40 |
| Modules, Jinax templates, context, loaders, and escaping | 10 | 38 |
| Health checks, metrics, mail, tasks, and WebSocket routing | 10 | 41 |
| **Total** | **100** | **514** |

## Run

Use Python 3.11 or newer and install the framework's test dependencies:

```bash
pip install -e ".[standard,dev,admin]"
python -m pytest tests/expanded -q -o addopts=''
python -m ruff check tests/expanded
python -m ruff format --check tests/expanded
```

The command clears the repository's default coverage options to run this suite
independently; it does not assert a coverage percentage. Tests use isolated
applications and temporary storage. Expiration tests control clocks instead of
sleeping, and mail adapter tests send no external email. The new suite needs
no external database or Redis server. The existing full suite includes a Redis
integration test and optional dependency, browser, and Python-version checks.

## Regressions fixed alongside these tests

- Invalid UUID HTTP and WebSocket path values now fail route matching instead
  of raising during converter casts.
- Non-ASCII JWT signatures raise `Unauthorized`; malformed password hashes
  return `False` instead of leaking `TypeError`.
- Trusted hosts reject userinfo, paths, query strings, fragments, malformed
  IPv6, invalid ports, and whitespace in HTTP authorities.
- Signed-cookie decoding splits at the final signature separator, preserving
  fractional timestamps and dots in application data. Malformed signatures
  return `None`.
- Composite template loaders fall through when Jinja2 raises
  `TemplateNotFound`, allowing module templates to supply missing app pages.
- CSS escaping imports its regex dependency and terminates hexadecimal
  escapes so following characters cannot extend them.

These regression tests strengthen the existing suite; they are not a claim
that every framework feature or security boundary has been exhaustively tested.

## Verification

On Python 3.12, the expanded suite passed all 514 cases. The full repository
suite passed with 836 passed and 26 skipped, using a temporary local Redis
server, the current local Teloce source checkout, and MinifyJS 0.1.3. The skipped
checks require optional drivers, browser setup, or newer Python versions.
The full run used `python -m pytest -q -o addopts=''`.

All new tests pass Ruff lint and format checks. Repository-wide Ruff still
reports existing findings; comparison against main found no new findings.
`mypy .` stops on duplicate example modules named `app` on both this branch
and unchanged main. This change does not claim a passing repository-wide
type check or coverage threshold.
