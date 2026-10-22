"""Admin registrations for the Discord-clone example.

These are ordinary flaxon.db (Tortoise) models, so the Admin registry derives
list views, search, filters and edit forms from the field definitions — no
boilerplate here. This is a deliberate use of Flaxon Admin: staff can moderate
users, servers and messages without any custom admin code. Application data is
deliberately kept OUT of Admin where it needs bespoke permission logic (e.g.
private-channel access), which remains in services.access.
"""
from __future__ import annotations

from models import (
    Bot,
    BotMembership,
    BotToken,
    Channel,
    ChannelAccess,
    CommandInvocation,
    EventDelivery,
    EventSubscription,
    Membership,
    Message,
    Role,
    Server,
    SlashCommand,
    User,
)


def register(admin) -> None:
    admin.register(
        User,
        list_display=["id", "username", "display_name", "email", "is_active"],
        search_fields=["username", "email", "display_name"],
        list_filter=["is_active"],
        fields=["username", "display_name", "email", "is_active", "avatar_color"],
        ordering=["username"],
    )
    admin.register(
        Server,
        list_display=["id", "name", "owner_id", "invite_code"],
        search_fields=["name", "invite_code"],
        fields=["name", "owner_id", "invite_code", "icon_color"],
        ordering=["name"],
    )
    admin.register(
        Channel,
        list_display=["id", "name", "server_id", "is_private"],
        search_fields=["name"],
        list_filter=["is_private"],
        fields=["name", "server_id", "topic", "is_private", "position"],
        ordering=["server_id", "position"],
    )
    admin.register(
        Role,
        list_display=["id", "name", "server_id", "permissions"],
        search_fields=["name"],
        fields=["name", "server_id", "permissions", "color", "position"],
        ordering=["server_id", "position"],
    )
    admin.register(
        Membership,
        list_display=["id", "server_id", "user_id", "role_id"],
        search_fields=["user_id", "server_id"],
        fields=["server_id", "user_id", "role_id", "nickname"],
        ordering=["server_id", "user_id"],
    )
    admin.register(
        Message,
        list_display=["id", "channel_id", "author_id", "author_bot_id", "type", "created_at"],
        search_fields=["content"],
        list_filter=["type"],
        fields=["channel_id", "author_id", "author_bot_id", "content", "type"],
        ordering=["-created_at"],
    )
    admin.register(
        Bot,
        list_display=["id", "name", "owner_id", "is_enabled"],
        search_fields=["name"],
        list_filter=["is_enabled"],
        fields=["name", "owner_id", "description", "is_enabled"],
        ordering=["name"],
    )
    admin.register(
        BotToken,
        list_display=["id", "bot_id", "label", "token_prefix", "revoked_at"],
        search_fields=["label", "token_prefix"],
        list_filter=["revoked_at"],
        fields=["bot_id", "label", "token_prefix"],
        ordering=["-created_at"],
    )
    admin.register(
        SlashCommand,
        list_display=["id", "bot_id", "name", "is_enabled"],
        search_fields=["name"],
        list_filter=["is_enabled"],
        fields=["bot_id", "name", "description", "parameters", "is_enabled"],
        ordering=["bot_id", "name"],
    )
    admin.register(
        EventSubscription,
        list_display=["id", "bot_id", "event_type", "is_enabled"],
        search_fields=["event_type"],
        list_filter=["is_enabled"],
        fields=["bot_id", "event_type", "is_enabled"],
        ordering=["bot_id", "event_type"],
    )
    admin.register(
        EventDelivery,
        list_display=["id", "bot_id", "event_type", "status", "attempt_count"],
        search_fields=["event_type"],
        list_filter=["status"],
        fields=["bot_id", "event_type", "status", "attempt_count", "last_error"],
        ordering=["-created_at"],
    )
    admin.register(
        CommandInvocation,
        list_display=["id", "bot_id", "command_id", "status", "created_at"],
        search_fields=["result", "error"],
        list_filter=["status"],
        fields=["bot_id", "command_id", "server_id", "user_id", "status", "result", "error"],
        ordering=["-created_at"],
    )
    # ChannelAccess is intentionally NOT registered as an editable Admin model:
    # it is a pure authorization table and is managed through the API only.
