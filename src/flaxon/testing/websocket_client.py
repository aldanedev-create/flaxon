from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any
from urllib.parse import urlsplit


class WebSocketClient:
    """Web socket client implementation for the testing subsystem."""

    def __init__(self, app: Any, base_url: str = "ws://testserver") -> None:
        self.app = app
        self.base_url = base_url.rstrip("/")
        self._socket = None
        self._receive_queue: asyncio.Queue = asyncio.Queue()
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._closed = False

    async def connect(self, path: str, headers: dict[str, str] | None = None) -> None:
        """Open the configured connection."""
        url = urlsplit(f"{self.base_url}{path}")
        raw_headers = [
            (key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in (headers or {}).items()
        ]

        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0", "spec_version": "2.5"},
            "http_version": "1.1",
            "scheme": url.scheme,
            "path": url.path or "/",
            "raw_path": (url.path or "/").encode("ascii"),
            "query_string": url.query.encode("utf-8") if url.query else b"",
            "headers": raw_headers,
            "client": ("127.0.0.1", 12345),
            "server": (url.hostname or "testserver", url.port or 80),
            "subprotocols": [],
        }

        self._closed = False
        self._receive_queue = asyncio.Queue()
        self._send_queue = asyncio.Queue()

        # An ASGI WebSocket application waits for this handshake message before
        # it can emit ``websocket.accept``.
        await self._send_queue.put({"type": "websocket.connect"})

        async def receive() -> dict[str, Any]:
            if self._closed:
                return {"type": "websocket.disconnect", "code": 1000}

            try:
                return await self._send_queue.get()
            except asyncio.CancelledError:
                return {"type": "websocket.disconnect", "code": 1000}

        async def send(message: dict[str, Any]) -> None:
            await self._receive_queue.put(message)

        self._task = asyncio.create_task(self.app(scope, receive, send))

        accept = await self._receive_queue.get()
        if accept.get("type") != "websocket.accept":
            raise RuntimeError("WebSocket connection rejected")

    async def disconnect(self, code: int = 1000) -> None:
        """Close the configured connection."""
        self._closed = True
        if self._task:
            await self._send_queue.put({"type": "websocket.disconnect", "code": code})
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=1.0)
            except TimeoutError:
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            self._task = None

    async def send_text(self, text: str) -> None:
        """Send the text."""
        await self._send_queue.put({"type": "websocket.send", "text": text})

    async def send_bytes(self, data: bytes) -> None:
        """Send the bytes."""
        await self._send_queue.put({"type": "websocket.send", "bytes": data})

    async def send_json(self, data: Any) -> None:
        """Send the json."""
        await self.send_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    async def receive_text(self) -> str:
        """Receive the text."""
        message = await self._receive_queue.get()
        if message.get("type") == "websocket.disconnect":
            raise RuntimeError("WebSocket disconnected")
        return message.get("text", "")

    async def receive_json(self) -> Any:
        """Receive the json."""
        text = await self.receive_text()
        return json.loads(text)

    async def __aenter__(self) -> WebSocketClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()


class AsyncWebSocketClient(WebSocketClient):
    """Async web socket client implementation for the testing subsystem."""

    def __init__(self, app: Any, base_url: str = "ws://testserver") -> None:
        super().__init__(app, base_url)
