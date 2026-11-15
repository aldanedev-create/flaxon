# Project templates

`flaxon new` can start from the smallest template that fits. You are never locked
in: every template is ordinary Flaxon code, and you can add a database, admin or
frontend later.

```bash
flaxon new --list-templates
flaxon new my-project --template api
```

| Template | Use it for | Includes | Does not include |
| --- | --- | --- | --- |
| `basic` | Learning, scripts, one-file services | Routes, health endpoint | Tests, modules, database |
| `api` | A JSON API without persistence | Modules, OpenAPI docs, trusted hosts, pytest | Database, admin, frontend tooling |
| `api-db` | A JSON API with persistence | `api` + Tortoise ORM, migrations, `management.py`, pytest | Admin, frontend tooling |
| `web` | A server-rendered website | Jinax templates, static files, HTML escaping, pytest | Database, admin, JavaScript build |
| `fullstack` (default) | An interactive app with admin | Teloce UI, Jinax, ORM, migrations, Admin/CMS | |

## What each one installs

Each template's `requirements.txt` names only the extras it needs, and
`requirements-dev.txt` adds test tools. The lean templates never import Teloce,
MinifyJS or pytscheck (a test in the framework's own suite enforces this).

| Template | `requirements.txt` |
| --- | --- |
| `basic`, `api`, `web` | `flaxon[standard]>=0.3.0` |
| `api-db` | `flaxon[standard,orm]>=0.3.0` |
| `fullstack` | `flaxon[standard,admin]>=0.3.0` |

## First run

`flaxon new` prints the exact commands for the template you chose. For `api`
and `web`:

```bash
python -m pip install -r requirements-dev.txt
python -m flaxon run app:app --reload
python -m pytest
```

For `api-db`, create and apply the first migration before running:

```bash
python management.py check
python management.py makemigrations
python management.py migrate
python management.py runserver
```

## Settings and production

`api` and `web` default to `DEBUG=false`. `api-db` and `fullstack` default to
`DEBUG=true` for local development; in production set `FLAXON_DEBUG=false` and a
persistent `FLAXON_SECRET_KEY` of at least 32 characters, or Flaxon refuses to
start. Every template restricts the `Host` header to `FLAXON_ALLOWED_HOSTS`, so
set it to your real hostnames before deploying.

## Moving up

- `api` to `api-db`: copy your modules over and add `models.py`, `settings.py`,
  `management.py` and `migrations/` from an `api-db` project.
- Any template to `fullstack`: see [Teloce SPA](Teloce-Spa.md) and
  [Admin and CMS](admin-cms.md); add them to the app factory when you need them.

Resume interrupted environment setup with
`flaxon new PATH --resume-venv`; Flaxon detects which template the project uses
from its files.
