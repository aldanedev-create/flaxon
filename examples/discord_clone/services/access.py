"""Access control: resolve a user's effective permissions inside a server.

The owner always has ADMINISTRATOR. Everyone else combines the server's
@everyone role with their assigned role. We deliberately keep this as a
single integer OR so the lesson stays about the bitmask, not ORM joins.
"""
from __future__ import annotations

from models import Membership, Role, Server
from services.permissions import (
    ADMINISTRATOR,
    DEFAULT_EVERYONE,
    has_flag,
)


async def get_membership(user_id: int, server_id: int) -> Membership | None:
    return await Membership.get_or_none(user_id=user_id, server_id=server_id)


async def effective_permissions(user_id: int, server_id: int) -> int:
    """Bitmask of what `user_id` may do in `server_id`."""
    server = await Server.get_or_none(id=server_id)
    if server is None:
        return 0
    if server.owner_id == user_id:
        return ADMINISTRATOR
    membership = await get_membership(user_id, server_id)
    if membership is None:
        return 0
    permissions = DEFAULT_EVERYONE
    if membership.role_id:
        role = await Role.get_or_none(id=membership.role_id)
        if role is not None:
            permissions |= role.permissions
    return permissions


async def check_permission(user_id: int, server_id: int, flag: int) -> bool:
    return has_flag(await effective_permissions(user_id, server_id), flag)


async def is_member(user_id: int, server_id: int) -> bool:
    return await get_membership(user_id, server_id) is not None


async def can_view_channel(user_id: int, server_id: int, is_private: bool) -> bool:
    """A member can view any channel; private channels still require membership."""
    return await is_member(user_id, server_id)
