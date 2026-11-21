"""WebSocket behavior over a real uvicorn server and a real client, where production failures live."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import time
import tomllib
from pathlib import Path

import pytest
import pytest_asyncio

pytest.importorskip("websockets")
pytest.importorskip("uvicorn")

import uvicorn
import websockets

from flaxon import Flaxon
from flaxon.exceptions import Forbidden, Unauthorized
from flaxon.websocket import (
    Heartbeat,
    WebSocket,
    WebSocketEvents,
    WebSocketManager,
    WebSocketOriginMiddleware,
)
from flaxon.websocket.authentication import WebSocketAuth, WebSocketAuthMiddleware


@contextlib.asynccontextmanager
async def serving(app: Flaxon, port: int):
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=port, log_level="critical", lifespan="on", timeout_graceful_shutdown=2
        )
    )
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    try:
        yield server
    finally:
        server.should_exit = True
        await task


async def eventually(check, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not check():
        assert time.monotonic() < deadline, "condition was not met in time"
        await asyncio.sleep(0.02)


async def close_code(connect) -> tuple[int, str]:
    """Open a connection and return the close code the server ended it with."""
    async with connect as ws:
        try:
            await asyncio.wait_for(ws.recv(), 3)
        except websockets.ConnectionClosed as closed:
            return closed.rcvd.code, closed.rcvd.reason
    raise AssertionError("the server did not close the connection")


def add_error_routes(app: Flaxon) -> None:
    @app.websocket("/ws/unauthorized")
    async def unauthorized(socket: WebSocket):
        await socket.accept()
        raise Unauthorized("token rejected")

    @app.websocket("/ws/forbidden")
    async def forbidden(socket: WebSocket):
        await socket.accept()
        raise Forbidden("not yours")

    @app.websocket("/ws/json")
    async def json_only(socket: WebSocket):
        await socket.accept()
        await socket.send_json(await socket.receive_json())

    @app.websocket("/ws/text")
    async def text_only(socket: WebSocket):
        await socket.accept()
        await socket.send_text(await socket.receive_text())

    @app.websocket("/ws/boom")
    async def boom(socket: WebSocket):
        await socket.accept()
        raise RuntimeError("secret internal detail")


@pytest_asyncio.fixture
async def app_and_url(unused_tcp_port):
    app = Flaxon("ws-production")
    add_error_routes(app)

    @app.websocket("/ws/echo")
    async def echo(socket: WebSocket):
        await socket.accept()
        await socket.send_json({"ready": True})
        async for message in socket.iter_json():
            await socket.send_json(message)

    @app.websocket("/ws/returns")
    async def returns(socket: WebSocket):
        await socket.accept()
        await socket.join("room")
        await socket.receive_text()  # then simply return, never calling close()

    @app.websocket("/ws/lingers")
    async def lingers(socket: WebSocket):
        await socket.accept()
        await socket.join("room")
        await asyncio.sleep(0.4)
        await socket.send_text("the peer is long gone")
        await asyncio.sleep(0.2)

    @app.websocket("/ws/room")
    async def room(socket: WebSocket):
        await socket.accept()
        await socket.join("chat")
        async for message in socket.iter_json():
            await socket.broadcast_json("chat", message)

    async with serving(app, unused_tcp_port):
        yield app, lambda path: f"ws://127.0.0.1:{unused_tcp_port}{path}"


# --- connections are always cleaned up ----------------------------------------------------------


@pytest.mark.asyncio
async def test_a_handler_that_simply_returns_does_not_leak_its_connection(app_and_url):
    app, url = app_and_url
    async with websockets.connect(url("/ws/returns")) as ws:
        await ws.send("bye")
        with contextlib.suppress(websockets.ConnectionClosed):
            await asyncio.wait_for(ws.recv(), 2)
    await eventually(lambda: not app.websocket_manager.connections and not app.websocket_manager.rooms)


@pytest.mark.asyncio
async def test_a_peer_that_vanishes_mid_handler_does_not_leak_its_connection(app_and_url):
    app, url = app_and_url
    ws = await websockets.connect(url("/ws/lingers"))
    await eventually(lambda: app.websocket_manager.connections)
    ws.transport.abort()  # no close handshake: the network just went away
    await eventually(lambda: not app.websocket_manager.connections and not app.websocket_manager.rooms)


@pytest.mark.asyncio
async def test_one_vanished_client_does_not_stop_the_chat_for_everyone_else(app_and_url):
    app, url = app_and_url
    async with websockets.connect(url("/ws/room")) as alice, websockets.connect(url("/ws/room")) as bob:
        carol = await websockets.connect(url("/ws/room"))
        await eventually(lambda: len(app.websocket_manager.members("chat")) == 3)
        carol.transport.abort()
        await alice.send('{"text": "hello"}')
        assert await asyncio.wait_for(alice.recv(), 3) == '{"text":"hello"}'
        assert await asyncio.wait_for(bob.recv(), 3) == '{"text":"hello"}'
    await eventually(lambda: not app.websocket_manager.connections)


# --- the client is told what went wrong ---------------------------------------------------------


@pytest.mark.asyncio
async def test_authorization_failures_are_reported_with_their_own_close_codes(app_and_url):
    _, url = app_and_url
    assert await close_code(websockets.connect(url("/ws/unauthorized"))) == (4401, "token rejected")
    assert await close_code(websockets.connect(url("/ws/forbidden"))) == (4403, "not yours")


@pytest.mark.asyncio
async def test_an_unknown_route_is_refused(app_and_url):
    _, url = app_and_url
    with pytest.raises(websockets.InvalidStatus) as refused:
        await websockets.connect(url("/ws/does-not-exist"))
    assert refused.value.response.status_code == 403


@pytest.mark.asyncio
async def test_bad_payloads_get_protocol_close_codes_not_a_server_error(app_and_url):
    _, url = app_and_url

    async def send_and_get_code(path: str, payload) -> tuple[int, str]:
        async with websockets.connect(url(path)) as ws:
            await ws.send(payload)
            with pytest.raises(websockets.ConnectionClosed) as closed:
                await asyncio.wait_for(ws.recv(), 3)
            return closed.value.rcvd.code, closed.value.rcvd.reason

    assert await send_and_get_code("/ws/json", "{not json") == (1007, "Invalid JSON")
    assert (await send_and_get_code("/ws/json", b"\x00\x01"))[0] == 1003
    assert (await send_and_get_code("/ws/text", b"\x00\x01"))[0] == 1003


@pytest.mark.asyncio
async def test_unhandled_errors_are_logged_and_never_leak_details_to_the_client(app_and_url, caplog):
    _, url = app_and_url
    with caplog.at_level(logging.ERROR, logger="flaxon.application.app"):
        code, reason = await close_code(websockets.connect(url("/ws/boom")))
    assert (code, reason) == (1011, "Internal server error")
    assert any("Unhandled WebSocket error" in record.message for record in caplog.records)
    assert "secret internal detail" not in reason


# --- the manager limits and shutdown ------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_connection_limit_refuses_new_peers_until_one_leaves(unused_tcp_port):
    app = Flaxon("limited")
    app.websocket_manager.max_connections = 1

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await socket.receive_text()

    async with serving(app, unused_tcp_port):
        url = f"ws://127.0.0.1:{unused_tcp_port}/ws"
        async with websockets.connect(url):
            await eventually(lambda: len(app.websocket_manager.connections) == 1)
            with pytest.raises(websockets.InvalidStatus):
                await websockets.connect(url)
        await eventually(lambda: not app.websocket_manager.connections)
        async with websockets.connect(url):  # there is room again
            pass


@pytest.mark.asyncio
async def test_shutdown_closes_connected_clients_and_empties_the_manager(unused_tcp_port):
    app = Flaxon("shutdown")

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await socket.join("room")
        await socket.receive_text()

    async with serving(app, unused_tcp_port) as server:
        client = await websockets.connect(f"ws://127.0.0.1:{unused_tcp_port}/ws")
        await eventually(lambda: app.websocket_manager.connections)
        server.should_exit = True
        with pytest.raises(websockets.ConnectionClosed) as closed:
            await asyncio.wait_for(client.recv(), 5)
        assert closed.value.rcvd.code in {1001, 1012}  # going away / service restart
    assert not app.websocket_manager.connections and not app.websocket_manager.rooms


# --- Origin validation (cross-site WebSocket hijacking) -----------------------------------------


@pytest_asyncio.fixture
async def origin_url(unused_tcp_port):
    app = Flaxon("origin")
    app.add_middleware(WebSocketOriginMiddleware, allowed_origins=["https://app.example.com"])

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await socket.send_json({"connected": True})

    async with serving(app, unused_tcp_port):
        yield lambda: f"ws://127.0.0.1:{unused_tcp_port}/ws", unused_tcp_port


@pytest.mark.asyncio
async def test_origin_check_blocks_foreign_sites_and_admits_the_right_ones(origin_url):
    url, port = origin_url

    async def attempt(origin: str | None) -> str:
        try:
            async with websockets.connect(url(), origin=origin) as ws:
                await ws.recv()
                return "accepted"
        except websockets.InvalidStatus as refused:
            return f"refused {refused.response.status_code}"

    assert await attempt("https://evil.example") == "refused 403"
    assert await attempt("null") == "refused 403"  # sandboxed pages and local files
    assert await attempt("https://app.example.com") == "accepted"
    assert await attempt("https://APP.example.com:443") == "accepted"  # same origin, different spelling
    assert await attempt(f"http://127.0.0.1:{port}") == "accepted"  # the server's own pages
    assert await attempt(None) == "accepted"  # non-browser clients send no Origin


@pytest.mark.parametrize(
    ("kwargs", "origin", "host", "expected"),
    [
        ({"allowed_origins": ["https://a.test"]}, b"https://a.test", b"x", True),
        ({"allowed_origins": ["https://a.test"]}, b"https://b.test", b"x", False),
        ({"allowed_origins": ["https://a.test"]}, b"http://a.test", b"x", False),  # scheme matters
        ({"allowed_origins": ["https://a.test"]}, b"https://a.test:8443", b"x", False),  # port matters
        ({"allowed_origins": ["*"]}, b"https://anything.test", b"x", True),
        ({}, b"https://site.test", b"site.test", True),  # same origin
        ({}, b"https://site.test", b"other.test", False),
        ({"allow_same_origin": False}, b"https://site.test", b"site.test", False),
        ({"allow_missing_origin": False}, None, b"site.test", False),
        ({}, b"javascript:alert(1)", b"site.test", False),
        ({}, b"", b"site.test", False),
    ],
)
def test_origin_policy_decisions(kwargs, origin, host, expected):
    middleware = WebSocketOriginMiddleware(app=None, **kwargs)
    headers = [(b"host", host)] + ([(b"origin", origin)] if origin is not None else [])
    assert middleware.is_allowed({"type": "websocket", "headers": headers}) is expected


def test_origin_middleware_rejects_malformed_configuration():
    with pytest.raises(ValueError, match="full origins"):
        WebSocketOriginMiddleware(app=None, allowed_origins=["app.example.com"])


@pytest.mark.asyncio
async def test_origin_middleware_ignores_plain_http_requests():
    reached = []

    async def app(scope, receive, send):
        reached.append(scope["type"])

    await WebSocketOriginMiddleware(app, allowed_origins=[])({"type": "http", "headers": []}, None, None)
    assert reached == ["http"]


# --- token expiry ---------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_unsigned_and_expiry_less_tokens_are_rejected():
    auth = WebSocketAuth("k" * 32)
    assert (await auth._validate_token(auth.create_token({"sub": "u1"}, expires_in=60)))["sub"] == "u1"
    assert await auth._validate_token(auth.create_token({"sub": "u1"}, expires_in=-1)) is None
    assert await auth._validate_token("not.a.token") is None
    assert await auth._validate_token("") is None
    assert await auth._validate_token("a.b.\u00e9") is None  # non-ASCII signature must not raise
    token = auth.create_token({"sub": "u1"}, expires_in=60)
    head, payload, signature = token.split(".")
    assert await auth._validate_token(f"{head}.{payload}.{signature[:-1]}0") is None

    def forge(claims: dict) -> str:
        body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        return f"{head}.{body}.{auth._sign(f'{head}.{body}')}"

    assert await auth._validate_token(forge({"sub": "u1"})) is None  # signed, but no expiry
    assert await auth._validate_token(forge({"sub": "u1", "exp": "never"})) is None
    assert await auth._validate_token(forge({"sub": "u1", "exp": True})) is None
    assert await auth._validate_token(forge({"sub": "u1", "exp": time.time() + 60})) is not None


@pytest.mark.asyncio
async def test_leeway_tolerates_small_clock_skew():
    strict, lenient = WebSocketAuth("k" * 32), WebSocketAuth("k" * 32, leeway=30)
    token = strict.create_token({"sub": "u1"}, expires_in=-5)
    assert await strict._validate_token(token) is None
    assert await lenient._validate_token(token) is not None


@pytest.mark.asyncio
async def test_authentication_middleware_end_to_end_with_expiry_and_query_token_switch(unused_tcp_port):
    auth = WebSocketAuth("k" * 32)

    def build(**options) -> Flaxon:
        app = Flaxon("auth")
        app.add_middleware(WebSocketAuthMiddleware, secret_key="k" * 32, **options)

        @app.websocket("/ws")
        async def ws(socket: WebSocket):
            await socket.accept()
            await socket.send_json({"user": socket.scope["user"]["sub"]})

        return app

    good = auth.create_token({"sub": "u1"}, expires_in=60)
    expired = auth.create_token({"sub": "u1"}, expires_in=-60)

    async def attempt(port: int, **connect) -> str:
        try:
            async with websockets.connect(
                f"ws://127.0.0.1:{port}/ws{connect.pop('query', '')}", **connect
            ) as ws:
                return str(await asyncio.wait_for(ws.recv(), 3))
        except websockets.InvalidStatus as refused:
            return f"refused {refused.response.status_code}"

    async with serving(build(), unused_tcp_port):
        assert await attempt(unused_tcp_port, query=f"?token={good}") == '{"user":"u1"}'
        assert await attempt(unused_tcp_port, query=f"?token={expired}") == "refused 403"
        assert (
            await attempt(unused_tcp_port, additional_headers={"Authorization": f"bearer {good}"})
            == '{"user":"u1"}'
        )
        assert await attempt(unused_tcp_port) == "refused 403"
    async with serving(build(allow_query_token=False), unused_tcp_port):
        assert await attempt(unused_tcp_port, query=f"?token={good}") == "refused 403"
        assert (
            await attempt(unused_tcp_port, additional_headers={"Authorization": f"Bearer {good}"})
            == '{"user":"u1"}'
        )


# --- the documented event API ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_documented_event_api_works(unused_tcp_port):
    app = Flaxon("events")
    seen: list = []

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        events = WebSocketEvents(socket)

        @events.on_connect
        async def connected():  # takes no arguments, as the docs show
            seen.append("connect")
            await socket.send_text("welcome")

        @events.on_message
        async def message(data):
            seen.append(("message", data))
            await socket.send_text(f"echo:{data}")

        @events.on_disconnect
        async def disconnected(code):
            seen.append(("disconnect", code))

        await events.run()

    async with serving(app, unused_tcp_port):
        async with websockets.connect(f"ws://127.0.0.1:{unused_tcp_port}/ws") as client:
            assert await asyncio.wait_for(client.recv(), 3) == "welcome"
            await client.send("hi")
            assert await asyncio.wait_for(client.recv(), 3) == "echo:hi"
        await eventually(lambda: ("disconnect", 1000) in seen)
    assert seen[0] == "connect" and ("message", "hi") in seen


# --- the documented heartbeat ------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_documented_heartbeat_keeps_live_clients_and_drops_silent_ones(unused_tcp_port):
    app = Flaxon("heartbeat")
    heartbeat = Heartbeat(interval=0.1, timeout=0.35)

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await heartbeat.start(socket)
        try:
            async for message in socket.iter_json():  # "pong" replies never reach this loop
                await socket.send_json({"echo": message})
        finally:
            await heartbeat.stop(socket)

    async with serving(app, unused_tcp_port):
        url = f"ws://127.0.0.1:{unused_tcp_port}/ws"

        async with websockets.connect(url) as alive:
            deadline = time.monotonic() + 1.0  # about three timeouts
            while time.monotonic() < deadline:
                with contextlib.suppress(TimeoutError):
                    if await asyncio.wait_for(alive.recv(), 0.1) == "ping":
                        await alive.send("pong")
            await alive.send('{"still": "here"}')
            echoed = False
            while not echoed:
                reply = await asyncio.wait_for(alive.recv(), 2)
                if reply == "ping":
                    await alive.send("pong")
                else:
                    echoed = reply == '{"echo":{"still":"here"}}'

        async with websockets.connect(url) as silent:  # never answers a ping
            with pytest.raises(websockets.ConnectionClosed) as closed:
                while True:
                    await asyncio.wait_for(silent.recv(), 3)
            assert closed.value.rcvd.code == 4408


# --- packaging ---------------------------------------------------------------------------------------


def test_the_standard_extras_can_actually_serve_websockets():
    """Plain uvicorn has no WebSocket implementation: every handshake would get HTTP 404."""
    extras = tomllib.loads((Path(__file__).resolve().parents[2] / "pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]
    for name in ("standard", "fullstack", "server"):
        assert any(
            dep.lower().startswith(("websockets", "wsproto", "uvicorn[standard]")) for dep in extras[name]
        ), name


def test_a_default_manager_has_sensible_limits():
    manager = WebSocketManager()
    assert manager.send_timeout == 10.0 and manager.max_connections is None
