import asyncio
from contextlib import asynccontextmanager
from typing import Any

import pytest

from flaxon import Flaxon
from flaxon.integrations.fastmcp import mount_fastmcp
from flaxon.testing import AsyncTestClient, TestClient


def test_pydantic_request_validation_and_response_serialization() -> None:
    pydantic = pytest.importorskip("pydantic")
    base_model = pydantic.BaseModel

    class User(base_model):
        name: str
        age: int

    app = Flaxon("pydantic-test", debug=True)

    @app.post("/users")
    async def create_user(user: User) -> User:
        return user

    client = TestClient(app)
    valid = client.post("/users", json_data={"name": "Ava", "age": 28})
    assert valid.status_code == 200
    assert valid.json() == {"name": "Ava", "age": 28}

    invalid = client.post("/users", json_data={"name": "Ava", "age": "not-a-number"})
    assert invalid.status_code == 422
    payload = invalid.json()
    assert payload["error"]["code"] == "FX-VAL-001"
    assert "age" in payload["error"]["fields"]


def test_fastmcp_mount_delegates_path_and_lifecycle() -> None:
    events: list[str] = []

    class MountedMCPApp:
        @asynccontextmanager
        async def lifespan(self, _app: Any):
            events.append("enter")
            yield
            events.append("exit")

        async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
            assert scope["path"] == "/"
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"mcp":true}',
                    "more_body": False,
                }
            )

    class FakeFastMCP:
        def http_app(self, **options: Any) -> MountedMCPApp:
            assert options["path"] == "/"
            assert options["stateless_http"] is True
            return MountedMCPApp()

    app = Flaxon("mcp-test", debug=True)
    mount_fastmcp(app, FakeFastMCP(), path="/mcp", stateless_http=True, require_auth=False)

    async def exercise_lifespan() -> None:
        messages = iter([
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
        ])
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return next(messages)

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await app({"type": "lifespan"}, receive, send)
        assert [item["type"] for item in sent] == [
            "lifespan.startup.complete",
            "lifespan.shutdown.complete",
        ]

    asyncio.run(exercise_lifespan())
    assert events == ["enter", "exit"]

    response = TestClient(app).get("/mcp")
    assert response.status_code == 200
    assert response.json() == {"mcp": True}


def test_real_fastmcp_http_app_mount() -> None:
    fastmcp = pytest.importorskip("fastmcp")
    server = fastmcp.FastMCP("integration-test")

    @server.tool
    def ping() -> str:
        return "pong"

    app = Flaxon("real-mcp-test", debug=True)
    mounted = mount_fastmcp(app, server, path="/mcp", require_auth=False)
    assert mounted is not None

    async def exercise() -> int:
        sent: list[dict[str, Any]] = []
        startup_done = asyncio.Event()
        shutdown_requested = asyncio.Event()
        first_message = True

        async def receive() -> dict[str, Any]:
            nonlocal first_message
            if first_message:
                first_message = False
                return {"type": "lifespan.startup"}
            await shutdown_requested.wait()
            return {"type": "lifespan.shutdown"}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)
            if message["type"] == "lifespan.startup.complete":
                startup_done.set()

        task = asyncio.create_task(app({"type": "lifespan"}, receive, send))
        await startup_done.wait()
        assert sent[0]["type"] == "lifespan.startup.complete"
        response = await AsyncTestClient(app).get("/mcp")
        shutdown_requested.set()
        await task
        assert sent[-1]["type"] == "lifespan.shutdown.complete"
        return response.status_code

    status_code = asyncio.run(exercise())
    assert status_code != 404


def test_fastmcp_mount_rejects_invalid_parent() -> None:
    with pytest.raises(RuntimeError, match="parent object"):
        mount_fastmcp(object(), object())


def test_fastmcp_mount_can_require_authentication() -> None:
    class FakeFastMCP:
        def http_app(self, **_options: Any) -> object:
            return object()

    app = Flaxon("secure-mcp-test")
    with pytest.raises(RuntimeError, match="require an auth provider"):
        mount_fastmcp(app, FakeFastMCP(), require_auth=True)
