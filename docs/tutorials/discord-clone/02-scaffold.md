# Lesson 2 — Scaffold the app with `flaxon new`

> **Track position:** you have read Lesson 1 and know the shape of the system.

## Goal

Turn an empty directory into a runnable Flaxon app with settings, migrations,
and an SPA shell.

## Step 1 — Generate the project

```bash
flaxon new discord_clone
cd discord_clone
```

The default template is `fullstack` (a modular Teloce app). You get:

```
app.py                    # application factory: mounts modules, Admin, CMS, Teloce
settings.py               # configuration; secrets from .env only
management.py             # one entry point: migrate, runserver, build, typecheck, setup-admin
models.py                 # root models
admin.py                  # Admin registrations
modules/welcome/          # example module: API route + its own UI component
ui/app.html               # SPA shell
public/app.css
templates/welcome.html
migrations/
requirements.txt
```

`management.py` is intentionally the thinnest possible wrapper — one entry point
for every command:

```python
from pathlib import Path
from flaxon.management import execute

def main(argv=None):
    return execute(argv, project_root=Path(__file__).resolve().parent)

if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 2 — Point settings at your own configuration

```python
# settings.py — the imports first, then the configuration
from pathlib import Path

from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
env.load(BASE_DIR / ".env")          # secrets come from a gitignored file

PROJECT_NAME = "discord-clone"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY", default="dev-only-discord-secret-change-me-32ch")
ALLOWED_HOSTS = env.list("FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{DATA_DIR / 'discord.sqlite3'}")
TIME_ZONE = "UTC"

# Redis is optional: only required for the multi-worker production topology.
REDIS_URL = env.str("REDIS_URL", default="")

ADMIN_ENABLED = True
CMS_ENABLED = True
ADMIN_STORE_BACKEND = "orm"
```

Two rules baked in here:

- `env.load(BASE_DIR / ".env")` loads secrets from a **gitignored** file, so no
  secret ever reaches source control.
- `REDIS_URL=""` is a real feature, not a placeholder: an empty value selects the
  in-memory broadcaster, which is what lets lessons 2–10 and the whole test suite
  run with zero infrastructure.

## Step 3 — Write the app factory

Ordering matters here:

```python
# app.py — every collaborator this factory touches, imported at the top
from __future__ import annotations

from flaxon import Flaxon, Request
from flaxon.admin.cms import CMSField, ContentType
from flaxon.db.admin import configure_admin

from admin import register as register_admin_models
from context import AppContext
from modules import accounts, bots, messages, realtime, servers
from settings import *  # noqa: F401,F403  (brings settings into scope for from_settings)


def create_app() -> Flaxon:
    app = Flaxon.from_settings()

    # 1. Teloce BEFORE the management guard so `build`/`typecheck` still work.
    app.use_teloce(project_root=settings.root, ui_dir="ui",
                   title="Discord Clone — System Design Course")

    # 2. Management commands need no routes, no Admin store, no DB reads.
    if app.is_management:
        return app

    # 3. Build the shared context and register it for injection.
    ctx = AppContext(secret_key=settings.SECRET_KEY, broadcaster=broadcaster)
    app.container.register_instance("ctx", ctx)

    # 4. Admin + CMS (both open DB-backed stores).
    admin = configure_admin(app)
    register_admin_models(admin)

    # 5. Mount API modules.
    app.mount_module(accounts, prefix="/api/auth")
    app.mount_module(servers, prefix="/api/servers")
    app.mount_module(messages, prefix="/api/messages")
    app.mount_module(bots, prefix="/api/bots")
    app.mount_module(realtime, prefix="/api/realtime")

    # 6. SPA catch-all LAST, and never shadow real routes.
    @app.get("/{spa_path:path}")
    async def spa(request, spa_path: str):
        if spa_path.startswith(("api/", "admin", "_flaxon", "static")):
            raise NotFound(spa_path)
        return await request.compile("app.html", {...})

    return app
```

**Why the `is_management` guard is load-bearing.** `configure_admin` opens the
Admin store, which *queries* admin tables at construction time. Those tables are
created by `migrate`. If Admin were configured before the guard, `migrate` would
fail on a fresh database trying to read tables it is about to create. Returning
early keeps management commands able to bootstrap the schema.

**Why the catch-all rejects API paths.** Without that guard, a typo like
`POST /api/servers` (no trailing slash) silently returns SPA HTML instead of a
clear 404/405.

## Step 4 — Keep the SPA shell

`ui/app.html` is your SPA root. Lessons 14–15 replace its contents; the file
itself stays.

## Verify

```bash
python management.py migrate     # applies models.0001_initial + flaxon_admin.0001_initial
python management.py runserver   # http://127.0.0.1:8000
```

Both must succeed on a clean database. If `migrate` fails with "no such table"
from the admin store, your `is_management` guard is in the wrong place.

## Why this way

One `management.py` entry point means every later command
(`makemigrations`, `build`, `typecheck`, `setup-admin`) is discoverable and
shares identical settings. Keeping the factory explicit — rather than magic
auto-discovery — means the boot order is readable, and boot order is exactly
what breaks when projects grow.

## Next

[Lesson 3 — The data model and migrations](03-data-model.md).
