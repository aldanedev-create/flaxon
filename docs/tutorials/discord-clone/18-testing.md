# Lesson 18: Testing the system

The course ships a pytest suite that exercises every layer. The harness
(`tests/conftest.py`) solves the three problems real Flaxon integration tests
hit:

1. **Migrations before import.** Importing `app` builds the admin store, which
   queries the database at construction, so migrations run in a *subprocess*
   before the app module is imported.
2. **Cookie- and CSRF-aware client.** `SessionClient` carries the session cookie
   between calls (browsers do; Flaxon's `TestClient` does not) and lazily fetches
   a CSRF token before the first mutation. The `make_session` fixture returns an
   isolated client per call.
3. **One IP, no rate limits.** All tests share `127.0.0.1`, so `RATE_LIMIT_ENABLED`
   is false and `REDIS_URL` is empty (in-memory broadcaster).

The suite is organised by concern: `test_auth`, `test_servers`, `test_messages`,
`test_bots`, `test_security`, `test_admin_cms`, `test_teloce`,
`test_multiworker`, and a full `test_journey`. Run it with:

```bash
pytest examples/discord_clone/tests -p no:asyncio -o addopts=
```

> `-p no:asyncio` disables pytest-asyncio's strict mode (the tests drive a
> synchronous `TestClient` that owns its own loop); `-o addopts=` drops the
> repo-wide coverage flags so the example run stays fast.

Two tests are worth reading as lessons themselves:
`test_multiworker.py` proves the cross-worker broadcast topology, and
`test_security.py` pins the CSRF and private-channel boundaries. A full
`test_journey.py` walks register → server → channel → message → bot → invoke →
logout end to end.

**Checkpoint:** run the suite; you should see **41 passed**. Add a test for a new
endpoint by reusing `make_session` and the `app`/`client` fixtures — never reach
into the database from a request test except to assert persistence.
