"""
WebSocket heartbeat for Flaxon.

This module provides heartbeat functionality for WebSocket connections
to detect and handle dead connections.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .connection import WebSocket, WebSocketDisconnect


class Heartbeat:
    """
    WebSocket heartbeat manager.

    This class manages heartbeat messages to keep WebSocket connections alive
    and detect dead connections.

    Example:
        ```python
        heartbeat = Heartbeat(interval=30, timeout=60)


        @app.websocket("/ws/chat")
        async def chat(socket: WebSocket):
            await socket.accept()
            await heartbeat.start(socket)
            try:
                async for message in socket.iter_json():
                    await socket.send_json({"echo": message})
            finally:
                await heartbeat.stop(socket)
        ```
    """

    def __init__(self, interval: int = 30, timeout: int = 60) -> None:
        """
        Initialize the heartbeat manager.

        Args:
            interval: The heartbeat interval in seconds.
            timeout: The timeout in seconds before considering a connection dead.
        """
        self.interval = interval
        self.timeout = timeout
        self._tasks: dict[WebSocket, asyncio.Task] = {}
        self._last_pong: dict[WebSocket, float] = {}
        self._lock = asyncio.Lock()

    async def start(self, socket: WebSocket) -> None:
        """
        Start heartbeat for a WebSocket connection.

        Args:
            socket: The WebSocket connection.
        """
        async with self._lock:
            if socket in self._tasks:
                return

            self._last_pong[socket] = time.time()
            task = asyncio.create_task(self._heartbeat_loop(socket))
            self._tasks[socket] = task

    async def stop(self, socket: WebSocket) -> None:
        """
        Stop heartbeat for a WebSocket connection.

        Args:
            socket: The WebSocket connection.
        """
        async with self._lock:
            task = self._tasks.pop(socket, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self._last_pong.pop(socket, None)

    async def _heartbeat_loop(self, socket: WebSocket) -> None:
        """Heartbeat loop for a connection."""
        try:
            while True:
                await asyncio.sleep(self.interval)

                last_pong = self._last_pong.get(socket, time.time())
                if time.time() - last_pong > self.timeout:
                    try:
                        await socket.close(1000, "Heartbeat timeout")
                    except Exception as exc:
                        logging.getLogger(__name__).warning("Isolated callback or cleanup failed (%s)", type(exc).__name__)
                    await self.stop(socket)
                    return

                try:
                    await socket.send_text("ping")
                except Exception:
                    await self.stop(socket)
                    return

        except asyncio.CancelledError:
            pass

    def pong_received(self, socket: WebSocket) -> None:
        """
        Record a pong response.

        Args:
            socket: The WebSocket connection.
        """
        self._last_pong[socket] = time.time()


class HeartbeatMiddleware:
    """
    Heartbeat middleware for WebSocket connections.

    This middleware adds heartbeat support to WebSocket connections.

    Example:
        ```python
        app.add_middleware(
            HeartbeatMiddleware,
            interval=30,
            timeout=60,
        )
        ```
    """

    def __init__(
        self, app: Any, interval: int = 30, timeout: int = 60
    ) -> None:
        """
        Initialize the heartbeat middleware.

        Args:
            app: The ASGI application.
            interval: The heartbeat interval in seconds.
            timeout: The timeout in seconds before considering a connection dead.
        """
        self.app = app
        self.heartbeat = Heartbeat(interval, timeout)

    async def __call__(
        self, scope: dict[str, Any], receive: Any, send: Any
    ) -> None:
        """Process the request with heartbeat support."""
        if scope.get("type") != "websocket":
            await self.app(scope, receive, send)
            return

        socket = WebSocket(scope, receive, send)

        async def receive_wrapper() -> dict[str, Any]:
            while True:
                try:
                    message = await receive()
                    if message.get("type") == "websocket.receive":
                        if "text" in message and message["text"] == "pong":
                            self.heartbeat.pong_received(socket)
                            continue
                    return message
                except WebSocketDisconnect:
                    await self.heartbeat.stop(socket)
                    raise

        async def send_wrapper(message: dict[str, Any]) -> None:
            await send(message)

        try:
            await self.heartbeat.start(socket)
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            await self.heartbeat.stop(socket)
