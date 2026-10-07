"""Proxy trust boundaries behavior and boundary cases."""

import pytest

from flaxon.middleware.proxy_headers import ProxyHeadersMiddleware


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "peer,trusted", [("192.0.2.1", []), ("192.0.2.1", None), ("198.51.100.1", ["192.0.2.1"]), (None, ["*"])]
)
async def test_untrusted_peers_cannot_rewrite_request(peer, trusted):
    captured = []

    async def downstream(scope, receive, send):
        captured.append(scope)

    middleware = ProxyHeadersMiddleware(downstream, trusted_proxies=trusted)
    scope = {
        "type": "http",
        "scheme": "http",
        "client": (peer, 1) if peer else None,
        "headers": [(b"x-forwarded-proto", b"https"), (b"x-forwarded-for", b"203.0.113.1")],
    }
    await middleware(scope, None, None)
    assert captured[0]["scheme"] == "http"
    assert captured[0]["client"] == scope["client"]


@pytest.mark.asyncio
async def test_trusted_proxy_selects_nearest_untrusted_peer():
    async def downstream(scope, receive, send):
        pass

    scope = {
        "type": "http",
        "client": ("10.0.0.2", 1),
        "scheme": "http",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.99, 198.51.100.7, 10.0.0.1"),
            (b"x-forwarded-proto", b"https"),
        ],
    }
    await ProxyHeadersMiddleware(downstream, trusted_proxies=["10.0.0.0/24"])(scope, None, None)
    assert scope["client"] == ("198.51.100.7", 0)
    assert scope["scheme"] == "https"
