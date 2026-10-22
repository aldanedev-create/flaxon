"""Channel messages: durable history and live delivery.

Every message is persisted by ``services.messages`` BEFORE the hub broadcasts it,
so a client that misses the WebSocket event still recovers the full history from
``GET /channels/<id>/messages``. The hub carries only live traffic.
"""
from __future__ import annotations

from flaxon.exceptions import BadRequest, NotFound

from context import AppContext
from models import Channel, Message
from modules._common import authorize_channel, int_param, json_body
from services import auth as auth_service
from services.bots import dispatch_message_event
from services.messages import MAX_HISTORY_LIMIT, create_message


messages = __import__("flaxon.modules", fromlist=["FlaxonModule"]).FlaxonModule("messages")
messages.requires("ctx")

MESSAGE_CREATE_LIMIT = (20, 10)  # generous; chat is bursty but bounded


async def _channel_and_server(channel_id: int, user_id: int) -> tuple[Channel, int]:
    channel = await Channel.get_or_none(id=channel_id)
    if channel is None:
        raise NotFound("Unknown channel")
    await authorize_channel(user_id, channel)
    return channel, channel.server_id


@messages.get("/<channel_id>/messages")
async def history(request, channel_id):
    user = await auth_service.require_user(request)
    cid = int_param(channel_id, "channel")
    channel = await Channel.get_or_none(id=cid)
    if channel is None:
        raise NotFound("Unknown channel")
    await authorize_channel(user.id, channel)
    before = request.query_params.get("before")
    limit = request.query_params.get("limit")
    before_id = int(before) if before and before.isdigit() else None
    limit_i = int(limit) if limit and limit.isdigit() else None
    if limit_i is not None:
        limit_i = max(1, min(limit_i, MAX_HISTORY_LIMIT))
    from services.messages import channel_history

    rows = await channel_history(cid, before_id=before_id, limit=limit_i or 50)
    return {"items": rows}


@messages.post("/<channel_id>/messages")
async def create(request, ctx: AppContext, channel_id):
    await ctx.guard(request, "msg", MESSAGE_CREATE_LIMIT)
    user = await auth_service.require_user(request)
    cid = int_param(channel_id, "channel")
    channel, server_id = await _channel_and_server(cid, user.id)
    payload = await json_body(request)
    content = str(payload.get("content", ""))
    try:
        message = await create_message(cid, author_id=user.id, content=content)
    except ValueError as exc:
        raise BadRequest(str(exc))
    # Persist first, then broadcast — a missed event is always recoverable.
    await ctx.hub.broadcast(cid, {
        "type": "message.create",
        "server_id": server_id,
        "channel_id": cid,
        "message": message.to_public(),
    })
    # Fire message.create to subscribed bots; their replies are real messages too.
    produced = await dispatch_message_event(message, server_id, hub=ctx.hub)
    return {"message": message.to_public(), "bot_messages": [m.to_public() for m in produced]}


@messages.delete("/<channel_id>/messages/<message_id>")
async def delete_message(request, ctx: AppContext, channel_id, message_id):
    user = await auth_service.require_user(request)
    cid = int_param(channel_id, "channel")
    mid = int_param(message_id, "message")
    channel, server_id = await _channel_and_server(cid, user.id)
    message = await Message.get_or_none(id=mid, channel_id=cid)
    if message is None:
        raise NotFound("Unknown message")
    # The author may always delete; a server owner may delete anything in it.
    if message.author_id != user.id:
        from services.access import is_member
        from services.permissions import ADMINISTRATOR, has_flag, effective_permissions

        perms = await effective_permissions(user.id, server_id)
        if not (has_flag(perms, ADMINISTRATOR) and await is_member(user.id, server_id)):
            raise BadRequest("You can only delete your own messages")
    await message.delete()
    await ctx.hub.broadcast(cid, {
        "type": "message.delete",
        "server_id": server_id,
        "channel_id": cid,
        "message_id": mid,
    })
    return {"ok": True}
