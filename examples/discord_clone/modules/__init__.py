"""FlaxonModules for the Discord-clone example.

Each module is a self-contained bundle of routes that declares the app-level
dependencies it needs (`requires("ctx")`) so a missing context fails at mount
time instead of on the first request. `app.py` mounts them all under /api.
"""
from modules.accounts import accounts
from modules.bots import bots
from modules.messages import messages
from modules.realtime import realtime
from modules.servers import servers

__all__ = ["accounts", "servers", "messages", "bots", "realtime"]
