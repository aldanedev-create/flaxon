# Lesson 1: What we are building and how to run it

Before any code, fix the shape of the system in your head. A Discord clone is
three concerns stacked together:

1. **Identity & authorization** — who you are (accounts) and what you may do
   (server membership, roles, a permission bitmask).
2. **Chat** — servers, channels, messages, and a live layer (presence, typing,
   new-message pushes) that sits *on top of* durable history.
3. **Extensibility** — a bot platform where third-party logic runs as registered
   handlers, not arbitrary code in your web process.

We keep these as separate Python modules and let Flaxon compose them. The
browser talks to a JSON API; a Teloce SPA renders the UI. The same API serves
both the human UI and the bot invoke/event surface, which is what makes the bot
platform "Discord-style".

**Why this is a system-design course, not a feature list.** Each phase isolates
one decision you would have to make in production:

- storing passwords (argon2, never plaintext),
- preventing cross-site request forgery on every mutation,
- authorizing at the API layer *and* in the database (private channels),
- keeping live traffic recoverable from durable history,
- making a bot platform safe (no untrusted code, tokens one-way hashed), and
- scaling realtime across multiple workers via a shared broadcaster.

**Checkpoint:** you can describe, in one sentence each, the job of `models.py`,
`modules/`, `admin.py`, and `ui/`. If you cannot, re-read the index before
continuing — the rest of the course is built on that separation.

## Run the finished project

The example is complete. Get it running first so every later lesson has a live
thing to poke at:

```bash
cd examples/discord_clone
python management.py migrate
python seed.py            # creates a demo user, server, channels, and a bot
python management.py runserver
```

Open the app at `http://127.0.0.1:8000` and the staff console at
`http://127.0.0.1:8000/admin/` (create an admin with
`python management.py setup-admin`). The seeded bot token is printed by
`seed.py`; you can also mint one from the UI's bot panel.

In the next lesson we scaffold the application shell these commands rely on.
