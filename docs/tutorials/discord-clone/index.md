# Build a Discord Clone + Bot Platform on Flaxon

This is a complete, runnable system-design course. You will build a small
Discord-style chat app **and** a Discord-style bot platform on top of the same
backend, using the four Flaxon subsystems this project teaches:

- **flaxon.db** — Tortoise ORM models + migrations (`models.py`)
- **flaxon.modules** — composable, dependency-injected route bundles (`modules/`)
- **flaxon.admin** — zero-boilerplate staff moderation of your models (`admin.py`)
- **flaxon.cms** — an editorial content type for announcements
- **Teloce** — the typed browser SPA (`ui/`)

The codebase lives in [`examples/discord_clone/`](../../examples/discord_clone/).
Every lesson points at the real files so you can read along.

## What you will build

A Discord clone with servers, channels, roles, messages, and live presence, plus
a bot platform where users create bots, issue one-time hashed tokens, register
slash commands, and subscribe to events that are delivered with idempotency and
retry. The final phase adds a **multi-worker** realtime layer: each worker owns
a hub, and hubs talk only through a broadcaster (in-memory in dev, Redis in
production).

## The seven phases

| Phase | Topic | Lesson |
|-------|-------|--------|
| 0 | Course overview & how to run | 1 |
| 1 | App scaffold (settings, management, modules) | 2 |
| 2 | Data model & migrations | 3 |
| 3 | App context & dependency injection | 4 |
| 4 | Authentication (sessions, argon2, CSRF) | 5 |
| 5 | Servers, channels, roles, permissions | 6 |
| 6 | Messages (durable history) | 7 |
| 7 | Bot platform: tokens & commands | 8 |
| 8 | Bot platform: events & idempotency | 9 |
| 9 | Realtime hub & broadcaster | 10 |
| 10 | Multi-worker topology | 11 |
| 11 | Flaxon Admin | 12 |
| 12 | Flaxon CMS | 13 |
| 13 | The Teloce SPA | 14 |
| 14 | Wiring UI to the API | 15 |
| 15 | Security review | 16 |
| 16 | Seed data & running | 17 |
| 17 | Testing the system | 18 |
| 18 | Deployment & next steps | 19 |

## Run it

```bash
cd examples/discord_clone
python management.py migrate
python seed.py            # optional demo data + a bot token
python management.py runserver
# open http://127.0.0.1:8000  and  http://127.0.0.1:8000/admin/
```

Tests:

```bash
pytest examples/discord_clone/tests -p no:asyncio
```

> The test suite disables pytest-asyncio's strict mode because the tests drive a
> synchronous `TestClient` that manages its own event loop; see
> `examples/discord_clone/tests/conftest.py`. It also forces an in-memory
> broadcaster (`REDIS_URL=""`) and turns off rate limiting (`RATE_LIMIT_ENABLED=false`)
> so every test shares one IP without tripping the demo limits.
