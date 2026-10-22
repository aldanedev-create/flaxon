# Lesson 19: Deployment and where to go next

The app is production-shaped. The only differences between dev and prod are
configuration, not code.

**Settings for production** (`settings.py` / `.env`):
- `FLAXON_SECRET_KEY` — a long, random value; never the dev default.
- `FLAXON_DEBUG=false`.
- `FLAXON_ALLOWED_HOSTS` — your domain(s).
- `DATABASE_URL` — Postgres (e.g. `postgres://user:pass@host/db`) instead of
  SQLite.
- `REDIS_URL` — set this to enable the `RedisBackedBroadcaster`, which is what
  makes the multi-worker realtime layer actually shared across processes
  (Lesson 11). Without it, each worker is isolated.

**Running multiple workers.** Behind a load balancer, run N copies of
`python management.py runserver` (or your ASGI server of choice). Because the
hubs share a Redis broadcaster, a message published on worker A reaches a socket
attached on worker B. Run at least two workers and kill one mid-session to
confirm live traffic survives.

**Scaling the bot platform.** Bot handlers run in-process by design. For heavy
bots, move `dispatch_message_event` to a job queue and keep the web process
light; the `EventDelivery` table already gives you idempotency and retry state.

**Where to go next:**
- Add presence/reaction models and surface them in the SPA.
- Replace the demo bot handlers with a webhook dispatcher that POSTs events to
  external bot URLs (use the stored token to authenticate them).
- Write Admin custom actions for bulk moderation; the Admin subsystem supports
  registered bulk actions.
- Read the framework docs in `docs/` — `architecture.md`, `security.md`, and the
  `guides/` directory — to take these patterns further.

**Final checkpoint:** you have a runnable Discord clone *and* a bot platform
built on Flaxon's ORM, modules, Admin, CMS, and Teloce — with a test suite that
proves the security and multi-worker boundaries. Change one thing at a time,
keep authorization in `_common.py`, and let the modules stay the unit of
organization as the project grows.
