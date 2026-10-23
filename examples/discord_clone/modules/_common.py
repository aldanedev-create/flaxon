"""Cross-cutting request helpers shared by every route module.

Kept in one place so the course can say "every mutating route does X" and mean
it: parse a JSON object, require a CSRF token, rate limit the caller, and load +
authorize the resource before touching it.
"""
from __future__ import annotations

from flaxon.exceptions import BadRequest, Forbidden, NotFound

from models import Channel, ChannelAccess
from services.access import effective_permissions, is_member
from services.permissions import ADMINISTRATOR, has_flag


async def json_body(request) -> dict:
    """Parse a JSON object body; anything else is a 400."""
    try:
        payload = await request.json()
    except Exception:
        raise BadRequest("Request body must be valid JSON")
    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a JSON object")
    return payload


def int_param(value: str, label: str = "id") -> int:
    """Convert a path segment to an id; a non-numeric id is a 404, not a 500."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise NotFound(f"Unknown {label}: {value}")


def require_csrf(ctx, request) -> None:
    """Reject state-changing requests without a valid CSRF token.

    Bot endpoints authenticate with a bearer token instead and are exempt: a bot
    client is not a browser, so it cannot be tricked into a cross-site request.
    """
    ctx.csrf.validate_request(request)


async def load_channel(channel_id: int) -> Channel:
    channel = await Channel.get_or_none(id=channel_id)
    if channel is None:
        raise NotFound("Unknown channel")
    return channel


async def authorize_channel(user_id: int, channel: Channel) -> Channel:
    """A user reaches a channel only through server membership.

    Private channels additionally require an explicit ``ChannelAccess`` grant;
    without one even a server member is refused.
    """
    if not await is_member(user_id, channel.server_id):
        raise Forbidden("You are not a member of this server")
    if channel.is_private and not await ChannelAccess.exists(
        user_id=user_id, channel_id=channel.id
    ):
        raise Forbidden("This channel is private")
    return channel


async def authorize_server(user_id: int, server_id: int, flag: int | None = None):
    """Load a server, require membership, and optionally require a permission."""
    from models import Server

    server = await Server.get_or_none(id=server_id)
    if server is None:
        raise NotFound("Unknown server")
    if not await is_member(user_id, server_id):
        raise Forbidden("You are not a member of this server")
    if flag is not None:
        permissions = await effective_permissions(user_id, server_id)
        if not (has_flag(permissions, flag) or has_flag(permissions, ADMINISTRATOR)):
            raise Forbidden("You do not have permission to do that")
    return server


def require_owner(server, user_id: int) -> None:
    if server.owner_id != user_id:
        raise Forbidden("Only the server owner can do that")
