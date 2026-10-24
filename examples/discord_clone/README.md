# Discord Clone + Bot Platform (Flaxon course project)

A complete, runnable system-design course built on Flaxon. It is a small
Discord-style chat app **and** a Discord-style bot platform on the same backend,
using the four Flaxon subsystems this project teaches:

- **flaxon.db** — Tortoise ORM models + migrations (`models.py`)
- **flaxon.modules** — dependency-injected route bundles (`modules/`)
- **flaxon.admin** — zero-boilerplate staff moderation (`admin.py`)
- **flaxon.cms** — an editorial "announcements" content type
- **Teloce** — the typed browser SPA (`ui/`)

The 19-lesson tutorial lives in
[`docs/tutorials/discord-clone/`](../../docs/tutorials/discord-clone/).

## Run it

```bash
python management.py migrate
python seed.py            # optional demo data + a one-time bot token
python management.py runserver
# app:      http://127.0.0.1:8000
# admin:    http://127.0.0.1:8000/admin/   (create an admin with setup-admin)
# build UI: python management.py build
```

Log in with the seeded `demo` / `password123`, or register a fresh account.

## Test it

```bash
pytest tests -p no:asyncio -o addopts=
```

41 tests cover auth, servers, channels, messages, the bot platform, security
(CSRF, private-channel isolation), Admin/CMS, the Teloce shell, and the
multi-worker realtime topology.

## Configuration (`.env`)

| Variable | Purpose | Default |
|----------|---------|---------|
| `FLAXON_SECRET_KEY` | session/CSRF signing | dev-only |
| `FLAXON_DEBUG` | debug mode | `true` |
| `DATABASE_URL` | ORM connection | SQLite in `data/` |
| `REDIS_URL` | shared broadcaster (multi-worker) | empty → in-memory |
| `RATE_LIMIT_ENABLED` | per-IP rate limiting | `true` |

Set `REDIS_URL` to a Redis URL to enable cross-worker realtime (Lesson 11).
