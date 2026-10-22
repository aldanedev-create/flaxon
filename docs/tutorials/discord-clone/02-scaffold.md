# Lesson 2: Scaffold the Flaxon app

A Flaxon project is deliberately small. Three files turn a directory into a
runnable app with migrations, settings, and an SPA:

- `settings.py` — configuration; secrets come only from `.env`.
- `management.py` — one entry point for `migrate`, `setup-admin`, `runserver`,
  `build`, `typecheck`.
- `app.py` — the application factory that mounts modules, Admin, CMS, and Teloce.

`examples/discord_clone/settings.py` keeps secrets out of source control:

```python
from pathlib import Path
from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
env.load(BASE_DIR / ".env")                       # never commit .env

SECRET_KEY = env.str("FLAXON_SECRET_KEY", default="dev-only-...")
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{BASE_DIR / 'data' / 'discord.sqlite3'}")
REDIS_URL = env.str("REDIS_URL", default="")      # empty => in-memory broadcaster
ADMIN_ENABLED = True
CMS_ENABLED = True
ADMIN_STORE_BACKEND = "orm"                        # admin metadata lives in the DB
```

`examples/discord_clone/management.py` is the thinnest possible wrapper:

```python
from pathlib import Path
from flaxon.management import execute

def main(argv=None):
    return execute(argv, project_root=Path(__file__).resolve().parent)

if __name__ == "__main__":
    raise SystemExit(main())
```

`app.py` shows the ordering that matters — Teloce is configured *before* the
management guard so build/typecheck still work, while Admin/CMS/modules only
build for the live app:

```python
def create_app() -> Flaxon:
    app = Flaxon.from_settings()
    app.use_teloce(project_root=settings.root, ui_dir="ui",
                   title="Discord Clone — System Design Course")
    if app.is_management:
        return app                       # migrate/build need no routes
    ctx = AppContext(secret_key=settings.SECRET_KEY, broadcaster=broadcaster)
    app.container.register_instance("ctx", ctx)   # DI target for modules
    admin = configure_admin(app)
    register_admin_models(admin)
    app.mount_module(accounts, prefix="/api/auth")
    # ... servers, messages, bots, realtime ...
    return app
```

**Checkpoint:** `python management.py migrate` applies two migration sets
(`models.0001_initial` and `flaxon_admin.0001_initial`) against the database URL
in your environment. `python management.py build` compiles the SPA into
`.flaxon/build`. If both succeed, the scaffold is correct.
