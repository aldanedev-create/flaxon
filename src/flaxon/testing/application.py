from __future__ import annotations

from typing import Any

from flaxon._imports import import_attribute


class TestApp:
    """Test app implementation for the testing subsystem."""

    def __init__(self, app: Any, config: dict[str, Any] | None = None) -> None:
        self.app = app
        self.config = config or {}

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        await self.app(scope, receive, send)

    def client(self) -> Any:
        # PLC0415: Local import retained to prevent circular imports with client modules
        """Perform the client operation for test app."""
        test_client_type = import_attribute("flaxon.testing.client", "TestClient")

        return test_client_type(self)

    def async_client(self) -> Any:
        """Perform the async client operation for test app."""
        async_test_client_type = import_attribute("flaxon.testing.client", "AsyncTestClient")

        return async_test_client_type(self)

    def websocket_client(self) -> Any:
        """Perform the websocket client operation for test app."""
        web_socket_client_type = import_attribute("flaxon.testing.websocket_client", "WebSocketClient")

        return web_socket_client_type(self)

    def async_websocket_client(self) -> Any:
        """Perform the async websocket client operation for test app."""
        async_web_socket_client_type = import_attribute(
            "flaxon.testing.websocket_client", "AsyncWebSocketClient"
        )

        return async_web_socket_client_type(self)

    def setup(self) -> None:
        """Configure the supplied application or resource."""
        if hasattr(self.app, "on_startup"):
            for handler in getattr(self.app, "on_startup", []):
                handler()

    def teardown(self) -> None:
        """Perform the teardown operation for test app."""
        if hasattr(self.app, "on_shutdown"):
            for handler in getattr(self.app, "on_shutdown", []):
                handler()
