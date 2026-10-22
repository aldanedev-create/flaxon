# Lesson 3: The data model and migrations

Everything durable lives in `examples/discord_clone/models.py` as Flaxon/Tortoise
models. Two kinds of state are modelled there:

- **Durable** — users, servers, channels, roles, memberships, messages, bots,
  tokens, commands, subscriptions, deliveries.
- **Ephemeral** — presence and typing are *not* modelled; they live in the
  realtime hub and are rebuilt from history on reconnect.

The schema encodes the authorization model directly. A server has members; a
member optionally holds a role; a role carries a permission bitmask. A private
channel is invisible to ordinary members unless a `ChannelAccess` row grants it —
isolation is enforced in the database, not just hidden in the UI:

```python
class Channel(Model):
    server = ForeignKeyField("models.Server", related_name="channels")
    name = CharField(max_length=100)
    is_private = BooleanField(default=False)

class ChannelAccess(Model):
    """Explicit grant letting a member read a private channel."""
    channel = ForeignKeyField("models.Channel", related_name="access_grants")
    user = ForeignKeyField("models.User", related_name="channel_access")
```

A bot's token stores only a SHA-256 hash and a short display prefix. The
plaintext token is returned to the owner exactly once and never persisted:

```python
class BotToken(Model):
    bot = ForeignKeyField("models.Bot", related_name="tokens")
    token_hash = CharField(max_length=64)     # SHA-256 hex
    token_prefix = CharField(max_length=12)   # human-readable prefix
    revoked_at = DatetimeField(null=True)
```

Event deliveries carry an idempotency key so retries never double-deliver:

```python
class EventDelivery(Model):
    bot = ForeignKeyField("models.Bot", related_name="deliveries")
    event_type = CharField(max_length=60)
    idempotency_key = CharField(max_length=64, db_index=True)
    status = CharField(max_length=16, default="pending")
    attempt_count = IntField(default=0)
```

**Checkpoint:** after editing a model, `python management.py makemigrations`
generates a migration and `migrate` applies it. Each model is automatically
exposed to Flaxon Admin (Lesson 12) with list views, search, and filters — no
code required. `ChannelAccess` is the one deliberate exception: it is pure
authorization and is managed through the API only.
