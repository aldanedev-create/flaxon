"""Cors credentials behavior and boundary cases."""

import pytest

from flaxon.http import Response
from flaxon.middleware.cors import CORSMiddleware


@pytest.mark.parametrize("origins", [None, ["*"], ["https://safe.example", "*"]])
def test_credentials_require_explicit_origins(origins):
    with pytest.raises(ValueError):
        CORSMiddleware(None, origins, allow_credentials=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("origin,allowed", [("https://safe.example", True), ("https://evil.example", False)])
async def test_preflight_only_grants_configured_origin(origin, allowed):
    messages = []

    async def downstream(scope, receive, send):
        raise AssertionError("preflight reached handler")

    async def send(message):
        messages.append(message)

    await CORSMiddleware(downstream, ["https://safe.example"], True)(
        {"type": "http", "method": "OPTIONS", "headers": [(b"origin", origin.encode())]}, None, send
    )
    assert messages[0]["status"] == 204
    headers = dict(messages[0]["headers"])
    assert (b"access-control-allow-origin" in headers) == allowed
    if allowed:
        assert headers[b"access-control-allow-credentials"] == b"true"


@pytest.mark.asyncio
async def test_origin_is_added_to_existing_vary():
    messages = []

    async def send(message):
        messages.append(message)

    middleware = CORSMiddleware(Response("ok", headers={"Vary": "Accept-Encoding"}), ["https://safe.example"])
    await middleware(
        {"type": "http", "method": "GET", "headers": [(b"origin", b"https://safe.example")]}, None, send
    )
    values = dict(messages[0]["headers"])[b"vary"].decode().lower()
    assert "origin" in values and "accept-encoding" in values
