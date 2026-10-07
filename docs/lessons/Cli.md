# CLI Reference

The `flaxon` command is installed automatically with the framework. Every command that takes an `application` argument expects it in `module:variable` form — the Python file (without `.py`) before the colon, the `Flaxon(...)` instance's variable name after it. Run these from the directory containing that file, or the app won't be importable.

```bash
flaxon --help          # list every command
flaxon --version       # show the installed Flaxon version
flaxon <command> --help  # full options for one command
```

## `flaxon run`

Starts your app with Uvicorn.

```bash
flaxon run app:app --reload
```

| Flag | Purpose |
|---|---|
| `--host HOST` | bind address (default `127.0.0.1`) |
| `--port PORT` | bind port (default `8000`) |
| `--reload` | auto-reload on file changes |
| `--workers N` | number of worker processes |
| `--log-level LEVEL` | logging verbosity |
| `--env-file FILE` | load environment variables from a file |

## `flaxon routes`

Lists every registered HTTP and WebSocket route.

```bash
$ flaxon routes app:app
Routes for bookstore
Method  Path                  Name
-----------------------------------------
GET     /                     home
GET     /books                list_books
POST    /books                create_book
DELETE  /books/<int:book_id>  delete_book
```

`--format json` or `--format csv` for machine-readable output, `--output FILE` to save instead of printing.

## `flaxon doctor`

Runs diagnostics against your app: confirms it imports, counts routes, flags missing configuration.

```bash
$ flaxon doctor app:app
Flaxon Doctor - bookstore
[PASS] Application imported successfully
[PASS] 4 HTTP route(s) registered
[PASS] 0 WebSocket route(s) registered
[WARN] A strong production SECRET_KEY is not configured.
Result: 1 warning(s), 0 failure(s)
```

`--fix` attempts automatic fixes for what it finds.

## `flaxon new`

Scaffolds a modular Flaxon + Teloce welcome application by default, including TypeScript, scoped component styles, a Python API, SQLite migrations, and a protected admin.

After generation, install the project, run `python management.py migrate`, and create your administrator with `python management.py setup-admin`. There is no default password. The generated project also includes `flaxon welcome` and `flaxon welcome-status`, registered by its welcome module through `flaxon_cli.py`. Use `--template basic` for the smaller API-only starter. See [getting started](../getting-started.md) for the complete workflow.

```bash
flaxon new my-project
```

`--template NAME` picks a starter template, `--no-venv` skips creating a virtualenv.

## `flaxon generate`

Scaffolds a single component — not a full project.

```bash
flaxon generate model Product
flaxon generate controller ProductController
flaxon generate service EmailService
```

Valid types: `controller`, `schema`, `service`, `middleware`, `model`, `task`. `--path DIR` sets where it's written (defaults to the current directory).

## `flaxon docs`

Generates an OpenAPI spec by reading your actual routes, endpoint docstrings, and `Schema`-typed parameters — no manual descriptions required for the basics.

```bash
$ flaxon docs app:app --title "Bookstore API"
✓ Wrote OpenAPI spec for 2 path(s) to openapi.json
```

| Flag | Purpose |
|---|---|
| `-o, --output FILE` | output path (default `openapi.json`) |
| `--title TITLE` | API title (default: your app's name) |
| `--version VERSION` | API version (default `1.0.0`) |
| `--indent N` | JSON indent width, `0` for compact (default `2`) |
| `--include-internal` | include Flaxon's own system routes (`/health`, `/metrics`, `/docs`, etc.) — excluded by default |

What actually gets extracted, automatically, from your code:
- **Summary/description** — your endpoint's docstring (first line = summary, rest = description).
- **Request body schema** — any parameter typed as a `Schema` subclass gets its fields, types, and constraints (`min_length`, `minimum`, etc.) pulled straight from the class definition.
- **Path parameters** — Flaxon's `<int:id>`-style converters get correctly typed and converted to OpenAPI's `{id}` format.

The output is a plain JSON file — hand-edit it afterward for anything auto-detection can't infer (security schemes, examples, descriptions on bare `int`/`str` parameters), or just re-run the command to regenerate the parts that come from your code.

## `flaxon inspect`

Shows detailed information about a running app's configuration.

```bash
$ flaxon inspect app:app --middleware --config
Application: bookstore
Debug: False
Middleware:
  - (<class 'flaxon.middleware.request_id.RequestIDMiddleware'>, {})
  - (<class 'flaxon.middleware.security_headers.SecurityHeadersMiddleware'>, {})
Config:
  ENV: development
  DEBUG: False
  SECRET_KEY: None
  ALLOWED_HOSTS: ['localhost', '127.0.0.1']
  MAX_BODY_SIZE: 10485760
  TRUSTED_PROXIES: []
  PROXY_HEADERS: ['x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host']
```

`--middleware` / `--config` toggle those sections; `--format {json,yaml,table}` controls output format.

## `flaxon build`

Wraps `python -m build` to produce a wheel and/or sdist for publishing.

```bash
flaxon build --format wheel
```

`--format {wheel,sdist,all}` (default `all`), `--output DIR` for the output directory.

## `flaxon test`

Wraps `pytest`.

```bash
flaxon test
flaxon test tests/test_routing.py --coverage -v
```

`--coverage` generates a coverage report, `--verbose`/`-v` for verbose output, `--keep-env` keeps the test environment around after the run. Requires `pytest` installed (`pip install flaxon[dev]` covers this).

## `flaxon shell`

Launches a Python REPL with your application already imported and available.

```bash
flaxon shell app:app
```

`--no-import` skips loading the application, for a plain Python shell.

## `flaxon migrate`

Applies or rolls back database migrations.

```bash
flaxon migrate --direction up
flaxon migrate --direction down --target 0003 --dry-run
```

`--direction {up,down}`, `--target VERSION` to migrate to a specific version, `--dry-run` to preview without applying.

## `flaxon schedule`

Runs your app's scheduled tasks (see `flaxon.tasks`).

```bash
flaxon schedule app:app --once
```

`--once` runs due tasks a single time and exits, instead of running continuously.

## `flaxon worker`

Starts a background worker process to consume tasks from a queue (see `flaxon.tasks`).

```bash
flaxon worker app:app --concurrency 4 --queue default
```

`--concurrency N` sets how many tasks run at once, `--queue NAME` picks which queue to consume from.

## `flaxon --version`

Prints the installed version.

```bash
$ flaxon --version
Flaxon 0.1.4
```