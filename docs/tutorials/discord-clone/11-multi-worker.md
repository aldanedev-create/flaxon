# Lesson 11: Multi-worker topology

This is the capstone systems lesson. Each Flaxon worker owns **one** `ChannelHub`.
If two workers each had their own in-process broadcaster, a message published on
worker A could never reach a socket attached on worker B — the naive, broken,
single-process behaviour.

The fix: hubs communicate *only* through a broadcaster. In production that is a
Redis Pub/Sub bridge (`RedisBackedBroadcaster`) that every worker shares. In dev
and tests we prove the same property with a single `MemoryBroadcaster` shared by
two hubs. The code under test does exactly that:

```python
broadcaster = MemoryBroadcaster()      # ONE instance
hub_a = ChannelHub(broadcaster)
hub_b = ChannelHub(broadcaster)        # both listen on the same broadcaster
sock_b = FakeSocket()
await hub_b.attach(sock_b, channel_id=1, user_id=2)
await asyncio.sleep(0.05)              # let hub_b subscribe
await hub_a.broadcast(1, {"type": "message.create", "id": 42})
await asyncio.sleep(0.1)               # traverse the broadcaster
assert any(m["id"] == 42 for m in sock_b.sent)   # crossed "workers"
```

Give each hub its *own* broadcaster and the event silently drops — which is the
test `test_separate_broadcasters_do_not_deliver` pins down. The lesson: realtime
scale is a topology decision (shared Redis broadcaster), not a code change in the
hub.

**Checkpoint:** read `tests/test_multiworker.py` and run it. It constructs both
topologies in-process and asserts the cross-worker delivery works only when the
broadcaster is shared. To run for real with Redis, set `REDIS_URL` in `.env`;
`app.py` then builds a `RedisBackedBroadcaster` instead of the in-memory one.
