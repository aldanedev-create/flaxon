# Lesson 11 — Multi-worker: making realtime survive more than one process

> **Track position:** realtime works — in one process. Now prove it works across
> several, and see exactly what breaks when it doesn't.

## Goal

Run N Flaxon workers behind a load balancer. A message sent on worker A must
reach a socket attached on worker B. Then **write the test that fails** for the
naive topology.

## System design

```mermaid
graph TD
    SPA1["Browser 1"] -->|WebSocket| W1["Worker A"]
    SPA2["Browser 2"] -->|WebSocket| W2["Worker B"]
    SPA1 -->|HTTP POST| LB["Load balancer"]
    SPA2 -->|HTTP GET| LB
    LB --> W1
    LB --> W2

    W1 --> H1["ChannelHub A"]
    W2 --> H2["ChannelHub B"]
    H1 <-->|"Pub/Sub channel '42'"| REDIS{{"Redis"}}
    H2 <-->|"Pub/Sub channel '42'"| REDIS
    W1 --> DB[("Postgres")]
    W2 --> DB
```

The two failure modes this topology must avoid:

```mermaid
graph TD
    subgraph Broken["Naive: broadcaster per worker"]
        BA["Hub A"] -->|publish| MA["MemoryBroadcaster A"]
        BB["Hub B"] -->|publish| MB["MemoryBroadcaster B"]
        MA -.->|"nothing crosses"| BB
    end
    subgraph Correct["Shared: one broadcaster"]
        CA["Hub A"] -->|publish| SH{{"Redis"}}
        CB["Hub B"] -->|subscribe| SH
    end
```

In dev, `MemoryBroadcaster` is constructed **once per process** — which is fine
while you run one process, and silently wrong the moment you run two. That is
precisely why `REDIS_URL` exists in `settings.py`.

## Step 1 — Select the broadcaster at startup

In `app.py`, after `app = Flaxon.from_settings()`:

```python
from context import AppContext

    # -- broadcaster: Redis in production, in-memory for dev/tests -----------
    if getattr(settings, "REDIS_URL", ""):
        from services.broadcaster import RedisBackedBroadcaster

        broadcaster = RedisBackedBroadcaster(settings.REDIS_URL)
    else:
        from services.broadcaster import MemoryBroadcaster

        broadcaster = MemoryBroadcaster()

    ctx = AppContext(secret_key=settings.SECRET_KEY, broadcaster=broadcaster)
    app.container.register_instance("ctx", ctx)
    app.on_startup(ctx.startup)
    app.on_shutdown(ctx.shutdown)
```

And in `settings.py`:

```python
from flaxon.config import env

# Redis is optional: only required for the multi-worker production topology.
REDIS_URL = env.str("REDIS_URL", default="")
```

Nothing else changes. Every module already receives `ctx` through DI — that is
the payoff of Lesson 4.

## Step 2 — The experiment: two hubs, one broadcaster

`tests/test_multiworker.py`, in full:

```python
"""Multi-worker realtime: hubs talk only through the Broadcaster."""
from __future__ import annotations

import asyncio

from services.broadcaster import MemoryBroadcaster
from services.hub import ChannelHub


class FakeSocket:
    """Stand-in for a WebSocket: records every JSON frame pushed to it."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, event: dict) -> None:
        self.sent.append(event)


async def _shared_broadcaster() -> bool:
    broadcaster = MemoryBroadcaster()      # ONE instance, two hubs
    hub_a = ChannelHub(broadcaster)
    hub_b = ChannelHub(broadcaster)

    sock_b = FakeSocket()
    await hub_b.attach(sock_b, channel_id=1, user_id=2)
    await asyncio.sleep(0.05)              # let hub_b's listener subscribe

    await hub_a.broadcast(1, {"type": "message.create", "id": 42})
    await asyncio.sleep(0.1)

    crossed = any(m.get("id") == 42 for m in sock_b.sent)
    await hub_b.detach(sock_b)
    return crossed


async def _separate_broadcasters() -> bool:
    hub_a = ChannelHub(MemoryBroadcaster())   # each hub, its own instance
    hub_b = ChannelHub(MemoryBroadcaster())

    sock_b = FakeSocket()
    await hub_b.attach(sock_b, channel_id=1, user_id=2)
    await asyncio.sleep(0.05)
    await hub_a.broadcast(1, {"type": "message.create", "id": 7})
    await asyncio.sleep(0.1)

    got = any(m.get("id") == 7 for m in sock_b.sent)
    await hub_b.detach(sock_b)
    return got


def test_shared_broadcaster_delivers_cross_worker():
    assert asyncio.run(_shared_broadcaster()) is True


def test_separate_broadcasters_do_not_deliver():
    assert asyncio.run(_separate_broadcasters()) is False
```

One `MemoryBroadcaster` instance shared by two hubs *is* the Redis topology,
modelled in memory. Two instances *is* the bug you would ship without this
lesson.

## Step 3 — Run it for real

```bash
# terminal 1
redis-server --port 6379

# .env
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgres://user:pass@localhost:5432/discord
FLAXON_SECRET_KEY=<32+ random chars>

# terminals 2 and 3 — two workers, distinct ports
python management.py runserver --port 8001
python management.py runserver --port 8002
```

Open the SPA on each port, log in as two users in the same channel, and send a
message. The frame arrives on the *other* worker's socket.

With `REDIS_URL` unset, do the same — the message appears only for the sender's
worker. That difference is the entire lesson, and it takes one env var to see.

> **Sticky sessions are not required.** Because fan-out goes through Redis, a
> user's socket can live on any worker. If you ever find yourself needing
> session affinity to make WebSockets work, something is holding state in the
> wrong place.

## Verify

| Scenario | Expected |
|---|---|
| `test_shared_broadcaster_delivers_cross_worker` | passes |
| `test_separate_broadcasters_do_not_deliver` | passes (proves the negative) |
| Two workers + Redis, message from A | visible on B's socket |
| Two workers, no Redis | visible only on the sender's worker |
| Kill one worker, other keeps serving | hub re-subscribes after a Redis blip |

## Why this way

- **The hub is process-local by construction.** It holds sockets — objects that
  cannot and should not be shared. Everything cross-process goes through a
  serialisable channel.
- **Redis Pub/Sub, not a queue.** Realtime events are at-most-once and cheap to
  lose; the durable copy is the database row. A queue would imply delivery
  guarantees the live layer cannot honour, and would need ack/bookkeeping.
- **The negative test is as valuable as the positive one.** Pinning the broken
  behaviour means nobody "optimises" the shared broadcaster back into two.
- **No application code changes between dev and prod.** Only the injected
  implementation differs — that is dependency injection earning its keep.

## Next

[Lesson 12 — Flaxon Admin](12-admin.md).
