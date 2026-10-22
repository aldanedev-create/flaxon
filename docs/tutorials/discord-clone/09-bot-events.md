# Lesson 9: Bot platform — events and idempotency

When a message is created, the platform fires `message.create` to every bot that
is a member of that server and subscribed to that event. Bots are *not* notified
about messages in servers they have not joined — `dispatch_message_event`
checks `BotMembership` first.

The example handler replies when a message mentions the bot by name or contains
`!hello`:

```python
@event_handler("message.create")
async def on_message(ctx, payload):
    content = (payload.get("content") or "").lower()
    if "!hello" in content or ctx.bot.name.lower() in content:
        author_id = payload.get("author_id")
        await ctx.post_message(f"Hello <@{author_id}>! I'm {ctx.bot.name}. Try /ping.")
```

Delivery is **idempotent** and **retried with backoff**, mirroring a real webhook
dispatcher. The idempotency key is derived from the message id, so retrying a
delivery for the same message is a no-op:

```python
existing = await EventDelivery.get_or_none(
    bot_id=bot.id, idempotency_key=key, status="delivered")
if existing is not None:
    return existing, []        # already delivered — never double-send
delivery = await EventDelivery.create(..., idempotency_key=key, status="pending")
return await attempt_delivery(bot, delivery)
```

`attempt_delivery` runs the handlers, records the result, and increments
`attempt_count`. `retry_failed_deliveries` backs off proportional to prior
attempts (capped at 8s) so a transient handler error heals without hammering.

**Checkpoint:** join a bot to a server, mention it in a message, and confirm the
bot's reply comes back. Send two distinct messages and confirm exactly two
`EventDelivery` rows exist — no duplicates. This is exactly what
`tests/test_bots.py::test_event_delivery_is_idempotent` asserts.
