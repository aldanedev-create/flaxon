"""Permission model: a bitmask on each Role.

ADMINISTRATOR is the catch-all flag that implies every other permission,
mirroring how Discord's permission system works. Keeping permissions as a
single integer makes them trivial to store, compare, and explain.
"""
from __future__ import annotations

VIEW_CHANNEL = 1
SEND_MESSAGES = 2
MANAGE_MESSAGES = 4
MANAGE_CHANNELS = 8
MANAGE_MEMBERS = 16
KICK_MEMBERS = 32
BAN_MEMBERS = 64
MANAGE_ROLES = 128
MANAGE_SERVER = 256
ADMINISTRATOR = 512

# A freshly joined member can read and talk, nothing more.
DEFAULT_EVERYONE = VIEW_CHANNEL | SEND_MESSAGES

# Human-readable names for the Admin/API surfaces.
FLAG_NAMES = {
    VIEW_CHANNEL: "View Channels",
    SEND_MESSAGES: "Send Messages",
    MANAGE_MESSAGES: "Manage Messages",
    MANAGE_CHANNELS: "Manage Channels",
    MANAGE_MEMBERS: "Manage Members",
    KICK_MEMBERS: "Kick Members",
    BAN_MEMBERS: "Ban Members",
    MANAGE_ROLES: "Manage Roles",
    MANAGE_SERVER: "Manage Server",
    ADMINISTRATOR: "Administrator",
}


def has_flag(permissions: int, flag: int) -> bool:
    return bool(permissions & flag)


def expand(permissions: int) -> list[str]:
    """Return the names of every flag set in a permission bitmask."""
    return [name for flag, name in FLAG_NAMES.items() if permissions & flag]
