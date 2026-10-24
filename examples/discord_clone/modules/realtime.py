"""Real-time transport: WebSocket channel subscriptions, presence, typing.

A browser opens ONE socket and subscribes to the channel it is currently
viewing. Authorisation is enforced on every subscribe, so a socket can never
receive traffic from a channel its user is not a member of. Durable messages
are not sent here — the client pulls history over HTTP and uses this socket for
live events only.
"""
from __future__ import annotations

import json

from flaxon.modules import FlaxonModule
from flaxon.security.sessions import SessionManager

from context import AppContext
from models import Channel
from modules._common import authorize_channel
from services import auth as auth_service


realtime = FlaxonModule("realtime")
realtime.requires("ctx")


def _ws_user_id(socket, secret_key: str) -> int | None:
    """Decode the signed session cookie from the WebSocket handshake headers."""
    cookies: dict[str, str] = {}
    for name, value in socket.scope.get("headers", []):
        if name == b"cookie":
            for part in value.decode("latin-1").split(";"):
                key, _, val = part.strip().partition("=")
                cookies[key.strip()] = val.strip()
            break
    if "session" not in cookies:
        return None
    manager = SessionManager(secret_key)
    session = manager.get_session(type("Req", (), {"cookies": cookies})())
    return session.to_dict().get("uid")


@realtime.websocket("/ws")
async def ws(socket, ctx: AppContext) -> None:
    user_id = _ws_user_id(socket, ctx.secret_key)
    if user_id is None:
        await socket.close(code=4401)
        return
    await socket.accept()
    current: int | None = None
    try:
        while True:
            message = await socket.receive()
            if message.get("type") != "websocket.receive":
                continue
            text = message.get("text", "")
            try:
                payload = json.loads(text)
            except (ValueError, TypeError):
                await socket.send_json({"type": "error", "message": "bad_json"})
                continue
            if not isinstance(payload, dict):
                continue
            ptype = payload.get("type")
            channel_id = payload.get("channel_id")

            if ptype == "subscribe" and channel_id:
                cid = int(channel_id)
                channel = await Channel.get_or_none(id=cid)
                if channel is None:
                    await socket.send_json({"type": "error", "message": "unknown_channel"})
                    continue
                try:
                    await authorize_channel(user_id, channel)
                except Exception:
                    await socket.send_json({"type": "error", "message": "forbidden"})
                    continue
                if current is not None and current != cid:
                    await ctx.hub.detach(socket)
                if current != cid:
                    await ctx.hub.attach(socket, cid, user_id)
                    current = cid
                await socket.send_json({
                    "type": "subscribed",
                    "channel_id": cid,
                    "presence": ctx.hub.presence_list(cid),
                    "typing": ctx.hub.typing_list(cid),
                })
            elif ptype == "typing" and channel_id and current == int(channel_id):
                await ctx.hub.publish_typing(int(channel_id), user_id)
            elif ptype == "unsubscribe" and channel_id:
                cid = int(channel_id)
                if current == cid:
                    await ctx.hub.detach(socket)
                    current = None
    except Exception:
        # Client disconnected or the receive loop ended; clean up below.
        pass
    finally:
        if current is not None:
            await ctx.hub.detach(socket)
