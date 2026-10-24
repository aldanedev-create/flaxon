# Discord Clone — Engineering Research Notebook (Phase 0)

> Verified against repo `aldanedev-create/flaxon` @ `e0ed04c` (branch `main`),
> flaxon package `src/flaxon/`, `teloce-py` 0.3.0, tortoise-orm 1.1.7, argon2 available.
> All claims below were read from source or a working example/test — not from docs alone.

## Flaxon ORM (`flaxon.db` = Tortoise 1.1.7 wrapper)
- Base: `from flaxon.db import Model, fields`. Root `models.py` is auto-discovered via `optional_module("models")` (app label `"models"`).
- PK: `id = fields.IntField(primary_key=True)` (auto-increment).
- Fields: `CharField(max_length=)`, `IntField`, `BooleanField(default=)`, `DatetimeField(auto_now_add=True / auto_now=True)`, `TextField`, `JSONField()`, `ForeignKeyField("models.User", related_name="x")`.
- FK target string form: `"models.<ClassName>"`.
- `class Meta: table = "dc_users"` (snake_case table name).
- Queries (async): `await User.create(...)`, `.get(id=)`, `.get_or_none(...)`, `.filter(...)`, `.all()`, `.count()`, `.update(...)`, `.delete()`, `.order_by("created_at")`, `.limit(n).offset(m)`, `.exists()`.
- Reverse FK: `await server.fetch_related("channels")` then `server.channels` (list). Filter by FK col: `.filter(server_id=sid)`.
- `app.db.initialize()` / `app.db.close()`; `DatabaseMiddleware` binds Tortoise context per request. Migrations via `management.py makemigrations` + `migrate` (Tortoise `Migration`/`ops.CreateModel`).
- `app.is_management` is True during management commands → skip templates/admin/cms in app.py.

## WebSocket (`src/flaxon/websocket/`)
- Declare: `@app.websocket("/ws/chat/<room_id>") async def chat(socket: WebSocket, room_id: str)`.
- Handler API (from whatsapp_chat example + connection.py): `await socket.accept()`, `await socket.join(room_id)`, `async for payload in socket.iter_json():`, `await socket.send_json({...})`, `await socket.leave(room_id)`. Exceptions: `WebSocketDisconnect`, `asyncio.CancelledError`.
- Handshake auth: read `socket.scope.get("query_string")` or headers (no first-class request object).
- `app.websocket_manager.broadcast_json(room_id, event)` → **process-local** RoomManager (rooms.py). This is the multi-worker failure.
- `RedisBroadcaster` exists (`websocket/redis_backend.py`, uses `redis.asyncio`): `publish(channel, message)`, async `subscribe(channel)` iterator.
  - Gotcha: `WebSocketManager.configure_broadcaster(broadcaster, rooms)` only spawns listeners for `rooms` present AT CALL TIME. Dynamic per-channel rooms miss events.
  - Decision: build own `ChannelHub` with pluggable broadcaster (Memory for dev/test, Redis for prod) to teach the pattern cleanly.

## Security (`src/flaxon/security/`)
- Password: module-level `hash_password(pw) -> str` (argon2 default), `verify_password(pw, hashed) -> bool`, `needs_rehash(hashed)`. MAINTAINED impl. USE THESE.
- Sessions: `request.session` is a dict-like object in route handlers (`request.session["uid"] = ...`, `request.session.get("uid")`). Signed-cookie session (ServerSideSessionStore? actually signed cookie) — no server-side store by default.
- CSRF: `CSRFMiddleware(app, secret_key)` validates `x-csrf-token` header (HMAC w/ secret_key, 1h validity). NOT auto-applied to app routes (only Admin mounts it). `CSRF(secret_key).generate_token()` issues a stateless token. Plan: mount middleware myself + `/api/csrf` GET to issue token to SPA.
- Rate limiting: `RateLimiter` is in-process, per client IP (`check(request.scope)`). Use directly in routes for login/register.
- API keys: `APIKeyManager` is in-memory, NOT persistent → bot tokens MUST be stored in ORM as SHA-256 hashes (one-way).

## Teloce frontend (`src/flaxon/teloce.py`)
- Mount: `app.use_teloce(ui_dir=BASE_DIR / "ui", title=..., description=...)` (called within app.py non-management mode). Compiled assets served under `/_flaxon`.
- Render shell: `await request.compile("app.html", context)` (or `teloce.render`).
- Components: `<template>/<script>/<style>` blocks. Syntax: `{{x}}`, `:prop`, `@click`, `v-if/v-else-if/v-else`, `v-for="item in items" :key="item.id"`, `v-model`. `data()`, `computed`, `methods`, `mounted`. Child import + `components: { Name }` kebab-case tags.
- Plain JS modules importable from components (island_architect imports `../static/js/*.js`). Use `fetch` for API.

## Admin (`src/flaxon/admin/`)
- `ADMIN_ENABLED = True`, `ADMIN_STORE_BACKEND = "orm"` (shares DATABASE_URL). `admin.py` with `def register(admin): admin.register(Model, list_display=[...], search_fields=[...], fields=[...], ordering=[...], list_filter=[...])` auto-discovered.
- `configure_admin(app)` returns the admin object; auto-loads admin.py's `register`.
- Use Admin to manage User/Server/Channel/Message/Bot (CRUD) — NOT websockets/bot-token secrets.

## CMS (`src/flaxon/admin/cms.py`)
- `CMS_ENABLED = True`; content stored as JSON dicts in Admin store (no public front-end, Admin-only). NOT suitable for chat messages (durable, high-volume, per-user). Use CMS for *course/static marketing pages* only, kept off the SPA routes.

## App skeleton (from school_portal / island_architect)
- `management.py`: `from flaxon.management import execute; execute(argv, project_root=Path(__file__).resolve().parent)`.
- `settings.py`: `env.load(BASE_DIR/".env")`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS` (include "testserver"), `DEBUG`, `ADMIN_ENABLED`, `ADMIN_STORE_BACKEND="orm"`.
- `app.py`: `app = Flaxon.from_settings()`; `if app.is_management: return app`; then mount static + teloce + admin.
- `app.db.initialize()` must run before ORM queries (tests call it explicitly).

## Test client
- `from flaxon.testing import TestClient, WebSocketClient`. `c = TestClient(app)`; `c.get/post/put/delete(path, json_data=...)`. `WebSocketClient(app).connect("/ws/...", headers={...})` / `.send_json` / `.receive_json` / `.disconnect()`.
- `redis`/`fakeredis`/`redis-server` are NOT installed → multi-worker test uses shared `MemoryBroadcaster` instance across two manager objects (single process) to simulate two workers without Redis.

## Design decisions (locked)
1. Auth users are app `User` rows, SEPARATE from Admin staff. Ordinary users cannot reach `/admin/*` (Admin own auth).
2. Bot tokens: plaintext shown once at creation, stored as SHA-256 (`token_hash`) + display `prefix`; revocation sets `revoked_at`.
3. Bot execution: handler functions registered in-process (safe, no arbitrary code exec).
4. Permissions: bitmask IntField on Role; ADMINISTRATOR implies all.
5. Presence/typing = ephemeral, in ChannelHub memory only; Messages = durable ORM.
6. Multi-worker lesson: naive `broadcast_json` (process-local) fails test #2; fix with RedisBroadcaster-backed ChannelHub.
