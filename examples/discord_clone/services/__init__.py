"""Backend service layer for the Discord-clone example.

Keeps route handlers thin. Each module here is independently testable and
documents one capability: access control, auth, tokens, rate limiting,
message persistence, the realtime hub, and the bot platform.
"""
