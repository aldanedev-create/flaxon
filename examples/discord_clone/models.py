"""Durable domain models for the Discord-clone example.

These are flaxon.db (Tortoise) models, so Flaxon Admin gets CRUD hooks for free.
Run `python management.py makemigrations` after any change here.

Two kinds of state live here:
- Durable: users, servers, channels, memberships, roles, messages, bots, tokens,
  commands, subscriptions, deliveries.
- Ephemeral (presence, typing) is intentionally NOT modelled here — it lives in
  the ChannelHub memory and is recovered from durable history on reconnect.
"""
from __future__ import annotations

from flaxon.db import Model, fields


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
class User(Model):
    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=40, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    display_name = fields.CharField(max_length=80, default="")
    password_hash = fields.CharField(max_length=255, null=True)
    avatar_color = fields.CharField(max_length=7, default="#5865f2")
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_users"

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "avatar_color": self.avatar_color,
        }


# --------------------------------------------------------------------------- #
# Guild / server topology
# --------------------------------------------------------------------------- #
class Server(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    owner = fields.ForeignKeyField("models.User", related_name="owned_servers")
    # Join code is not a secret: it is a shareable, rotatable invite handle.
    invite_code = fields.CharField(max_length=12, unique=True)
    icon_color = fields.CharField(max_length=7, default="#232428")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_servers"

    def to_public(self) -> dict:
        return {"id": self.id, "name": self.name, "icon_color": self.icon_color}


class Role(Model):
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField("models.Server", related_name="roles")
    name = fields.CharField(max_length=60)
    # Bitmask of permissions.* flags.
    permissions = fields.IntField(default=0)
    color = fields.CharField(max_length=7, default="#99aab5")
    position = fields.IntField(default=0)

    class Meta:
        table = "dc_roles"


class Membership(Model):
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField("models.Server", related_name="members")
    user = fields.ForeignKeyField("models.User", related_name="memberships")
    role = fields.ForeignKeyField("models.Role", related_name="members", null=True)
    nickname = fields.CharField(max_length=80, default="")
    joined_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_memberships"
        unique_together = (("server_id", "user_id"),)


class Channel(Model):
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField("models.Server", related_name="channels")
    name = fields.CharField(max_length=100)
    topic = fields.CharField(max_length=300, default="")
    is_private = fields.BooleanField(default=False)
    position = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_channels"
        indexes = (("server_id", "position"),)

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "server_id": self.server_id,
            "name": self.name,
            "topic": self.topic,
            "is_private": self.is_private,
            "position": self.position,
        }


class ChannelAccess(Model):
    """Explicit grant letting a member read a private channel.

    A private channel is invisible to ordinary members unless they hold a row
    here, so isolation is enforced in the database, not only in the UI.
    """

    id = fields.IntField(primary_key=True)
    channel = fields.ForeignKeyField("models.Channel", related_name="access_grants")
    user = fields.ForeignKeyField("models.User", related_name="channel_access")
    granted_by = fields.ForeignKeyField("models.User", related_name="granted_access", null=True)

    class Meta:
        table = "dc_channel_access"
        unique_together = (("channel_id", "user_id"),)


# --------------------------------------------------------------------------- #
# Messages — durable, authoritative history
# --------------------------------------------------------------------------- #
class Message(Model):
    TYPE_USER = 0
    TYPE_SYSTEM = 1
    TYPE_BOT = 2

    id = fields.IntField(primary_key=True)
    channel = fields.ForeignKeyField("models.Channel", related_name="messages")
    # Exactly one of author / author_bot is set.
    author = fields.ForeignKeyField("models.User", related_name="messages", null=True)
    author_bot = fields.ForeignKeyField("models.Bot", related_name="messages", null=True)
    content = fields.TextField()
    type = fields.IntField(default=TYPE_USER)
    edited_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_messages"
        indexes = (("channel_id", "created_at"),)

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "author_id": self.author_id,
            "author_bot_id": self.author_bot_id,
            "content": self.content,
            "type": self.type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
        }


# --------------------------------------------------------------------------- #
# Bot platform
# --------------------------------------------------------------------------- #
class Bot(Model):
    id = fields.IntField(primary_key=True)
    owner = fields.ForeignKeyField("models.User", related_name="bots")
    name = fields.CharField(max_length=80)
    description = fields.CharField(max_length=300, default="")
    is_enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_bots"

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "is_enabled": self.is_enabled,
        }


class BotToken(Model):
    """One-way stored bot credentials. The plaintext token is shown ONCE."""

    id = fields.IntField(primary_key=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="tokens")
    token_hash = fields.CharField(max_length=64)  # SHA-256 hex
    token_prefix = fields.CharField(max_length=12)  # human-readable prefix
    label = fields.CharField(max_length=80, default="default")
    created_at = fields.DatetimeField(auto_now_add=True)
    revoked_at = fields.DatetimeField(null=True)
    last_used_at = fields.DatetimeField(null=True)

    class Meta:
        table = "dc_bot_tokens"


class BotMembership(Model):
    """Grants a bot a role (and therefore scoped permissions) inside a server."""

    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField("models.Server", related_name="bot_members")
    bot = fields.ForeignKeyField("models.Bot", related_name="server_memberships")
    role = fields.ForeignKeyField("models.Role", related_name="bot_members", null=True)

    class Meta:
        table = "dc_bot_memberships"
        unique_together = (("server_id", "bot_id"),)


class SlashCommand(Model):
    id = fields.IntField(primary_key=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="commands")
    name = fields.CharField(max_length=32)
    description = fields.CharField(max_length=200, default="")
    # JSON list of {name, type, required, description}.
    parameters = fields.JSONField(default=list)
    is_enabled = fields.BooleanField(default=True)

    class Meta:
        table = "dc_commands"
        unique_together = (("bot_id", "name"),)


class EventSubscription(Model):
    id = fields.IntField(primary_key=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="subscriptions")
    event_type = fields.CharField(max_length=60)  # message.create, member.join, ...
    is_enabled = fields.BooleanField(default=True)

    class Meta:
        table = "dc_event_subscriptions"
        unique_together = (("bot_id", "event_type"),)


class EventDelivery(Model):
    """One outbound event dispatch to a bot, with retry/backoff tracking."""

    STATUS_PENDING = "pending"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"

    id = fields.IntField(primary_key=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="deliveries")
    subscription = fields.ForeignKeyField(
        "models.EventSubscription", related_name="deliveries", null=True
    )
    event_type = fields.CharField(max_length=60)
    # Opaque, deduplicated per (bot_id, idempotency_key).
    idempotency_key = fields.CharField(max_length=64, db_index=True)
    payload = fields.JSONField(default=dict)
    status = fields.CharField(max_length=16, default=STATUS_PENDING)
    attempt_count = fields.IntField(default=0)
    last_error = fields.CharField(max_length=500, null=True)
    delivered_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_event_deliveries"


class CommandInvocation(Model):
    """Record of a slash command executed by a bot (result or error)."""

    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"

    id = fields.IntField(primary_key=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="invocations")
    command = fields.ForeignKeyField("models.SlashCommand", related_name="invocations")
    server_id = fields.IntField(null=True)
    channel_id = fields.IntField(null=True)
    user_id = fields.IntField(null=True)
    status = fields.CharField(max_length=16, default=STATUS_SUCCESS)
    result = fields.TextField(default="")
    error = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dc_command_invocations"
