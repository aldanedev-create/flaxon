"""Session cookie signature behavior and boundary cases."""

import pytest

from flaxon.sessions.backends.memory import MemoryBackend
from flaxon.sessions.manager import SessionManager


@pytest.mark.asyncio
async def test_signed_cookie_loads_only_matching_session():
    manager = SessionManager(MemoryBackend(), "secret", cookie_secure=True)
    session = await manager.create({"user": "alice"})
    header = manager.create_cookie(session)
    value = header.split(";", 1)[0].split("=", 1)[1]
    assert (await manager.get_from_cookie(value))["user"] == "alice"
    assert "Secure" in header and "HttpOnly" in header and "SameSite=Lax" in header
    assert manager.parse_cookie(value + "tampered") is None
    assert SessionManager(MemoryBackend(), "other").parse_cookie(value) is None


@pytest.mark.parametrize("value", ["", "unsigned", "id:", ":invalid"])
def test_malformed_cookies_do_not_load(value):
    assert SessionManager(MemoryBackend(), "secret").parse_cookie(value) is None


def test_deletion_cookie_expires_browser_value():
    header = SessionManager(MemoryBackend(), "secret").delete_cookie()
    assert header.startswith("session=;") and "Max-Age=0" in header
