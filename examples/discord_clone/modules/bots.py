"""Bot platform HTTP API.

Bots are owned by users. A bot's token is shown once and stored only as a
SHA-256 hash (services.tokens). Slash commands and event subscriptions are
registered here; actual execution lives in services.bots.
"""
from __future__ import annotations

from flaxon.exceptions import BadRequest, Forbidden, NotFound

from context import AppContext
from models import (
    Bot,
    BotMembership,
    BotToken,
    EventSubscription,
    SlashCommand,
)
from modules._common import int_param, json_body, require_csrf
from services import auth as auth_service
from services.bots import execute_command
from services.tokens import issue_token, revoke_token
from services.access import is_member


bots = __import__("flaxon.modules", fromlist=["FlaxonModule"]).FlaxonModule("bots")
bots.requires("ctx")

BOT_CREATE_LIMIT = (5, 60)


@bots.get("")
async def list_bots(request):
    user = await auth_service.require_user(request)
    rows = await Bot.filter(owner_id=user.id).order_by("-created_at")
    return {"items": [b.to_public() for b in rows]}


@bots.post("")
async def create_bot(request, ctx: AppContext):
    await ctx.guard(request, "bot-create", BOT_CREATE_LIMIT)
    user = await auth_service.require_user(request)
    payload = await json_body(request)
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 80:
        raise BadRequest("A bot name of 1-80 characters is required")
    bot = await Bot.create(
        owner=user,
        name=name,
        description=str(payload.get("description", ""))[:300],
        is_enabled=bool(payload.get("is_enabled", True)),
    )
    # A fresh bot starts subscribed to message.create so the example handler works.
    await EventSubscription.create(bot=bot, event_type="message.create")
    raw, _token = await issue_token(bot, label="default")
    return {"bot": bot.to_public(), "token": raw}


@bots.get("/<bot_id>")
async def get_bot(request, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    return {"bot": bot.to_public()}


@bots.delete("/<bot_id>")
async def delete_bot(request, ctx: AppContext, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    bot.is_enabled = False
    await bot.save(update_fields=["is_enabled"])
    return {"ok": True}


@bots.post("/<bot_id>/join")
async def join_server(request, ctx: AppContext, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    payload = await json_body(request)
    server_id = int_param(str(payload.get("server_id", "")), "server")
    from models import Server

    server = await Server.get_or_none(id=server_id)
    if server is None:
        raise NotFound("Unknown server")
    if not await is_member(user.id, server_id):
        raise Forbidden("You must be a member of the server to add a bot")
    if await BotMembership.exists(server_id=server_id, bot_id=bot.id):
        return {"ok": True, "already": True}
    await BotMembership.create(server=server, bot=bot)
    return {"ok": True}


@bots.get("/<bot_id>/tokens")
async def list_tokens(request, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    rows = await BotToken.filter(bot_id=bot.id)
    return {
        "items": [
            {
                "id": t.id,
                "label": t.label,
                "prefix": t.token_prefix,
                "revoked": t.revoked_at is not None,
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
            }
            for t in rows
        ]
    }


@bots.post("/<bot_id>/tokens")
async def create_token(request, ctx: AppContext, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    payload = await json_body(request)
    label = str(payload.get("label", "default"))[:80]
    raw, _token = await issue_token(bot, label=label)
    return {"token": raw, "prefix": _token.token_prefix}


@bots.delete("/<bot_id>/tokens/<token_id>")
async def revoke_one(request, ctx: AppContext, bot_id, token_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    record = await BotToken.get_or_none(id=int_param(token_id, "token"), bot_id=bot.id)
    if record is None:
        raise NotFound("Unknown token")
    await revoke_token(record.id)
    return {"ok": True}


@bots.post("/<bot_id>/commands")
async def create_command(request, ctx: AppContext, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    payload = await json_body(request)
    name = str(payload.get("name", "")).strip().lower()
    if not name or len(name) > 32 or not name.replace("-", "").isalnum():
        raise BadRequest("A command name of 1-32 letters/digits/hyphens is required")
    command = await SlashCommand.update_or_create(
        bot=bot, name=name,
        defaults={
            "description": str(payload.get("description", ""))[:200],
            "parameters": payload.get("parameters", []) or [],
            "is_enabled": bool(payload.get("is_enabled", True)),
        },
    )
    obj = command[0]
    return {"command": {"id": obj.id, "name": obj.name, "enabled": obj.is_enabled}}


@bots.post("/<bot_id>/subscriptions")
async def create_subscription(request, ctx: AppContext, bot_id):
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    payload = await json_body(request)
    event_type = str(payload.get("event_type", "")).strip()
    if not event_type:
        raise BadRequest("event_type is required")
    await EventSubscription.update_or_create(
        bot=bot, event_type=event_type,
        defaults={"is_enabled": bool(payload.get("is_enabled", True))},
    )
    return {"ok": True}


@bots.post("/<bot_id>/invoke")
async def invoke(request, ctx: AppContext, bot_id):
    """Run a slash command as the calling user inside a channel.

    This is the in-app entry point the example bot uses; an external caller
    would authenticate with a bearer token instead (see services.tokens).
    """
    user = await auth_service.require_user(request)
    bot = await _owned_bot(user.id, int_param(bot_id, "bot"))
    if not bot.is_enabled:
        raise BadRequest("Bot is disabled")
    payload = await json_body(request)
    channel_id = int_param(str(payload.get("channel_id", "")), "channel")
    from models import Channel

    channel = await Channel.get_or_none(id=channel_id)
    if channel is None:
        raise NotFound("Unknown channel")
    if not await is_member(user.id, channel.server_id):
        raise Forbidden("You are not a member of this server")
    if not await BotMembership.exists(server_id=channel.server_id, bot_id=bot.id):
        raise BadRequest("This bot is not in that server")
    command = await SlashCommand.get_or_none(bot_id=bot.id, name=str(payload.get("command", "")).strip().lower())
    if command is None:
        raise NotFound("Unknown command")
    invocation, produced = await execute_command(
        bot, command,
        server_id=channel.server_id, channel_id=channel_id,
        user_id=user.id, args=payload.get("args", []),
    )
    for m in produced:
        await ctx.hub.broadcast(channel_id, {
            "type": "message.create",
            "server_id": channel.server_id,
            "channel_id": channel_id,
            "message": m.to_public(),
        })
    return {
        "invocation": {"id": invocation.id, "status": invocation.status, "result": invocation.result, "error": invocation.error},
        "messages": [m.to_public() for m in produced],
    }


async def _owned_bot(user_id: int, bot_id: int) -> Bot:
    bot = await Bot.get_or_none(id=bot_id)
    if bot is None:
        raise NotFound("Unknown bot")
    if bot.owner_id != user_id:
        raise Forbidden("You do not own this bot")
    return bot
