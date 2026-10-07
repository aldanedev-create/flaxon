"""Websocket route converters behavior and boundary cases."""

from uuid import UUID

import pytest

from flaxon.routing.route import WebSocketRoute


async def handler(socket):
    pass


def test_uuid_socket_route_keeps_typed_identifier():
    value = "12345678-1234-5678-1234-567812345678"
    route = WebSocketRoute("/ws/<uuid:room>", handler)
    assert route.match("/ws/" + value) == {"room": UUID(value)}


@pytest.mark.parametrize("value", ["-" * 36, "not-a-uuid", "12345678-1234-5678-1234-56781234567z"])
def test_malformed_uuid_socket_route_does_not_raise(value):
    assert WebSocketRoute("/ws/<uuid:room>", handler).match("/ws/" + value) is None


def test_integer_socket_route_preserves_signed_numbers():
    route = WebSocketRoute("/ws/<int:room>", handler)
    assert route.match("/ws/-2") == {"room": -2}
    assert route.match("/ws/two") is None
