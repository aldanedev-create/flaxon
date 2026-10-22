"""Servers, channels, roles and memberships.

Mounted at ``/api/servers``. Note what is deliberately *not* here: no admin
panel and no content pages — those are Flaxon Admin and Flaxon CMS, enabled in
``settings.py`` and configured in ``app.py`` / ``admin.py``.
"""
from __future__ import annotations

import secrets

from flaxon.exceptions import BadRequest, NotFound
from flaxon.modules import FlaxonModule

from context import AppContext
from models import Channel, ChannelAccess, Membership, Role, Server, User
from modules._common import (
    authorize_server,
    int_param,
    json_body,
    require_csrf,
    require_owner,
)
from services import auth as auth_service
from services.access import effective_permissions, is_member
from services.permissions import (
    ADMINISTRATOR,
    MANAGE_CHANNELS,
    MANAGE_MEMBERS,
    MANAGE_ROLES,
    MANAGE_SERVER,
    expand,
    has_flag,
)

servers = FlaxonModule("servers")
servers.requires("ctx")

SERVER_CREATE_LIMIT = (10, 60)


def _invite_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "_")[:10]


def _public(server: Server) -> dict:
    return {**server.to_public(), "owner_id": server.owner_id, "invite_code": server.invite_code}


@servers.get("")
async def list_servers(request):
    user = await auth_service.require_user(request)
    memberships = await Membership.filter(user_id=user.id).prefetch_related("server").all()
    return {"items": [_public(m.server) for m in memberships]}


@servers.post("")
async def create_server(request, ctx: AppContext):
    require_csrf(ctx, request)
    await ctx.guard(request, "server-create", SERVER_CREATE_LIMIT)
    user = await auth_service.require_user(request)
    payload = await json_body(request)
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 100:
        raise BadRequest("A server name of 1-100 characters is required")
    server = await Server.create(name=name, owner=user, invite_code=_invite_code())
    # The owner is always the first member, carrying the baseline @everyone role.
    await Membership.create(server=server, user=user)
    await Channel.create(server=server, name="general", position=0)
    return {"server": _public(server)}


@servers.get("/<server_id>")
async def get_server(request, server_id):
    user = await auth_service.require_user(request)
    server = await authorize_server(user.id, int_param(server_id, "server"))
    return {
        "server": _public(server),
        "permissions": expand(await effective_permissions(user.id, server.id)),
    }


@servers.patch("/<server_id>")
async def update_server(request, ctx: AppContext, server_id):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    server = await authorize_server(user.id, int_param(server_id, "server"), MANAGE_SERVER)
    require_owner(server, user.id)
    payload = await json_body(request)
    if payload.get("name") is not None:
        server.name = str(payload["name"]).strip()[:100]
        await server.save(update_fields=["name"])
    if payload.get("rotate_invite"):
        server.invite_code = _invite_code()
        await server.save(update_fields=["invite_code"])
    return {"server": _public(server)}


@servers.post("/join")
async def join_server(request, ctx: AppContext):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    payload = await json_body(request)
    code = str(payload.get("invite_code", "")).strip()
    server = await Server.get_or_none(invite_code=code)
    if server is None:
        raise NotFound("No server with that invite code")
    if not await is_member(user.id, server.id):
        await Membership.create(server=server, user=user)
    return {"server": _public(server)}


@servers.get("/<server_id>/members")
async def list_members(request, server_id):
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    await authorize_server(user.id, sid)
    memberships = await Membership.filter(server_id=sid).prefetch_related("user", "role").all()
    return {
        "items": [
            {
                "user": m.user.to_public(),
                "nickname": m.nickname,
                "role": m.role.name if m.role else "everyone",
                "role_color": m.role.color if m.role else "#99aab5",
            }
            for m in memberships
        ]
    }


@servers.get("/<server_id>/channels")
async def list_channels(request, server_id):
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    await authorize_server(user.id, sid)
    channels = await Channel.filter(server_id=sid).order_by("position", "id").all()
    visible = []
    for channel in channels:
        if channel.is_private and not await ChannelAccess.exists(
            user_id=user.id, channel_id=channel.id
        ):
            continue
        visible.append(channel.to_public())
    return {"items": visible}


@servers.post("/<server_id>/channels")
async def create_channel(request, ctx: AppContext, server_id):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    server = await authorize_server(user.id, sid, MANAGE_CHANNELS)
    payload = await json_body(request)
    name = str(payload.get("name", "")).strip().lower()
    if not name or len(name) > 100:
        raise BadRequest("A channel name of 1-100 characters is required")
    is_private = bool(payload.get("is_private", False))
    channel = await Channel.create(
        server=server,
        name=name,
        topic=str(payload.get("topic", ""))[:300],
        is_private=is_private,
        position=int(payload.get("position", 0) or 0),
    )
    if is_private:
        # The creator can always see the private channel they just made.
        await ChannelAccess.create(channel=channel, user=user, granted_by=user)
    await ctx.hub.broadcast(
        sid, {"type": "channel.created", "server_id": sid, "channel": channel.to_public()}
    )
    return {"channel": channel.to_public()}


@servers.get("/<server_id>/roles")
async def list_roles(request, server_id):
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    await authorize_server(user.id, sid)
    roles = await Role.filter(server_id=sid).order_by("position", "id").all()
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "color": r.color,
                "permissions": r.permissions,
                "permission_names": expand(r.permissions),
            }
            for r in roles
        ]
    }


@servers.post("/<server_id>/roles")
async def create_role(request, ctx: AppContext, server_id):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    server = await authorize_server(user.id, sid, MANAGE_ROLES)
    payload = await json_body(request)
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 60:
        raise BadRequest("A role name of 1-60 characters is required")
    role = await Role.create(
        server=server,
        name=name,
        permissions=int(payload.get("permissions", 0) or 0),
        color=str(payload.get("color", "#99aab5"))[:7],
        position=int(payload.get("position", 0) or 0),
    )
    return {
        "role": {
            "id": role.id,
            "name": role.name,
            "permissions": role.permissions,
            "permission_names": expand(role.permissions),
        }
    }


async def _resolve_user(user_ref: str) -> User:
    target = await User.get_or_none(username=user_ref)
    if target is None:
        target = await User.get_or_none(id=int_param(user_ref, "user"))
    if target is None:
        raise NotFound("Unknown user")
    return target


@servers.post("/<server_id>/members/<user_ref>/role")
async def assign_role(request, ctx: AppContext, server_id, user_ref):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    await authorize_server(user.id, sid, MANAGE_ROLES)
    target = await _resolve_user(user_ref)
    payload = await json_body(request)
    role_id = payload.get("role_id")
    role = await Role.get_or_none(id=role_id, server_id=sid) if role_id else None
    membership = await Membership.get_or_none(server_id=sid, user_id=target.id)
    if membership is None:
        raise NotFound("That user is not a member")
    membership.role = role
    await membership.save(update_fields=["role_id"])
    return {"ok": True, "role": role.name if role else "everyone"}


@servers.delete("/<server_id>/members/<user_ref>")
async def kick_member(request, ctx: AppContext, server_id, user_ref):
    require_csrf(ctx, request)
    user = await auth_service.require_user(request)
    sid = int_param(server_id, "server")
    server = await authorize_server(user.id, sid)
    permissions = await effective_permissions(user.id, sid)
    can_manage = has_flag(permissions, MANAGE_MEMBERS) or has_flag(permissions, ADMINISTRATOR)
    if not can_manage and server.owner_id != user.id:
        raise BadRequest("You cannot remove members")
    target = await _resolve_user(user_ref)
    if target.id == server.owner_id:
        raise BadRequest("The owner cannot be removed")
    removed = await Membership.filter(server_id=sid, user_id=target.id).delete()
    if not removed:
        raise NotFound("That user is not a member")
    return {"ok": True}
