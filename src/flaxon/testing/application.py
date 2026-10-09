from __future__ import annotations

from typing import Any


class TestApp:

    def __init__(self, app: Any, config: dict[str, Any] | None = None) -> None:
        self.app = app
        self.config = config or {}

    async def __call__(
        self, scope: dict[str, Any], receive: Any, send: Any
    ) -> None:
        await self.app(scope, receive, send)

    def client(self) -> Any:
        # PLC0415: Local import retained to prevent circular imports with client modules
        from .client import TestClient

        return TestClient(self)

    def async_client(self) -> Any:
        from .client import AsyncTestClient

        return AsyncTestClient(self)

    def websocket_client(self) -> Any:
        from .websocket_client import WebSocketClient

        return WebSocketClient(self)

    def async_websocket_client(self) -> Any:
        from .websocket_client import AsyncWebSocketClient

        return AsyncWebSocketClient(self)

    def setup(self) -> None:
        if hasattr(self.app, "on_startup"):
            for handler in getattr(self.app, "on_startup", []):
                handler()

    def teardown(self) -> None:
        if hasattr(self.app, "on_shutdown"):
            for handler in getattr(self.app, "on_shutdown", []):
                handler()
