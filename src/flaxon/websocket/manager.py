"""WebSocket connection and room manager.

The manager tracks open connections and named rooms for one process. Broadcasts are delivered
concurrently, a peer that fails or is too slow is dropped instead of affecting the others, and, when
a :class:`~flaxon.websocket.broadcaster.Broadcaster` is configured, rooms are shared across worker
processes.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

#: Close code for "the server is shutting down or restarting".
GOING_AWAY = 1001
#: Close code used when a peer cannot keep up with what is sent to it.
SLOW_CONSUMER = 1013
_RECONNECT_START = 0.5
#: Marks a message published by a manager, so a worker can skip its own messages.
_ENVELOPE = "__flaxon_ws__"
_RECONNECT_MAX = 30.0


class WebSocketManager:
    """Track connections and broadcast rooms for an application.

    Args:
        broadcaster: Shares rooms across processes (for example Redis). Can also be set later with
            :meth:`configure_broadcaster`.
        send_timeout: Seconds to wait for one peer to accept a broadcast message before it is dropped
            as a slow consumer. ``None`` waits forever.
        max_connections: Refuse new connections once this many are open. ``None`` means no limit.
    """

    def __init__(
        self,
        broadcaster: Any | None = None,
        *,
        send_timeout: float | None = 10.0,
        max_connections: int | None = None,
    ) -> None:
        self.connections: set[Any] = set()
        self.rooms: dict[str, set[Any]] = {}
        self.broadcaster = broadcaster
        self.send_timeout = send_timeout
        self.max_connections = max_connections
        self._memberships: dict[Any, set[str]] = {}
        self._listeners: dict[str, asyncio.Task[Any]] = {}
        self._pinned: set[str] = set()
        self._origin = uuid.uuid4().hex

    @property
    def has_capacity(self) -> bool:
        """Whether another connection may be accepted."""
        return self.max_connections is None or len(self.connections) < self.max_connections

    def members(self, room: str) -> tuple[Any, ...]:
        """Connections currently in a room."""
        return tuple(self.rooms.get(room, ()))

    async def connect(self, socket: Any) -> None:
        """Register an accepted connection."""
        self.connections.add(socket)

    async def disconnect(self, socket: Any) -> None:
        """Forget a connection and remove it from every room. Safe to call more than once."""
        self.connections.discard(socket)
        for room in self._memberships.pop(socket, ()):
            self._remove(room, socket)

    async def join(self, room: str, socket: Any) -> None:
        """Add the connection to the named room."""
        self.rooms.setdefault(room, set()).add(socket)
        self._memberships.setdefault(socket, set()).add(room)
        self._listen_if_shared(room)

    async def leave(self, room: str, socket: Any) -> None:
        """Remove the connection from the named room. Leaving a room that does not exist is a no-op."""
        joined = self._memberships.get(socket)
        if joined is not None:
            joined.discard(room)
            if not joined:
                del self._memberships[socket]
        self._remove(room, socket)

    def _remove(self, room: str, socket: Any) -> None:
        members = self.rooms.get(room)
        if members is None:
            return
        members.discard(socket)
        if not members:
            del self.rooms[room]
            if room not in self._pinned and (task := self._listeners.pop(room, None)) is not None:
                task.cancel()

    async def broadcast_json(self, room: str, value: Any) -> None:
        """Send a JSON message to every connection in a room.

        Connections on this worker receive it immediately. With a broadcaster, it is also published so
        the other workers deliver it to theirs; if publishing fails (for example Redis is down) this
        worker's connections still get the message and the failure is logged. A peer that fails or is
        too slow is dropped; the others still receive it.
        """
        await self._deliver(self.members(room), value)
        if self.broadcaster is not None:
            try:
                await self.broadcaster.publish(room, {_ENVELOPE: 1, "origin": self._origin, "data": value})
            except Exception as exc:  # losing cross-worker delivery must not crash the sender
                logger.error(
                    "WebSocket broadcast to room %r was not published (%s)", room, type(exc).__name__
                )

    async def _deliver(self, sockets: tuple[Any, ...], value: Any) -> None:
        if not sockets:
            return
        failed = [
            socket for socket in await asyncio.gather(*(self._send(s, value) for s in sockets)) if socket
        ]
        for socket in failed:
            await self._evict(socket)

    async def _send(self, socket: Any, value: Any) -> Any | None:
        """Send to one peer. Returns the socket if it failed or timed out, otherwise ``None``."""
        try:
            await asyncio.wait_for(socket.send_json(value), self.send_timeout)
        except Exception as exc:  # a dead or slow peer must never affect the others
            logger.debug("Dropping WebSocket after failed send (%s)", type(exc).__name__)
            return socket
        return None

    async def _evict(self, socket: Any) -> None:
        await self.disconnect(socket)
        close = getattr(socket, "close", None)
        if close is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(close(SLOW_CONSUMER, "Too slow to keep up"), 1.0)

    # ----------------------------------------------------------------- cross-worker rooms

    async def configure_broadcaster(self, broadcaster: Any, rooms: set[str] | None = None) -> None:
        """Share rooms across workers using a Broadcaster implementation.

        Every room with local members, and every room named in ``rooms``, is subscribed. Rooms joined
        later are subscribed automatically, and a subscription that drops is re-established.
        """
        self.broadcaster = broadcaster
        self._pinned |= set(rooms or ())
        for room in {*self.rooms, *self._pinned}:
            self._listen_if_shared(room)

    def _listen_if_shared(self, room: str) -> None:
        if self.broadcaster is not None and room not in self._listeners:
            self._listeners[room] = asyncio.create_task(self._listen(room), name=f"flaxon-ws-room-{room}")

    async def _listen(self, room: str) -> None:
        """Deliver broadcasts for one room, re-subscribing after errors with exponential backoff."""
        delay = _RECONNECT_START
        while (broadcaster := self.broadcaster) is not None:
            try:
                async for message in broadcaster.subscribe(room):
                    delay = _RECONNECT_START
                    if isinstance(message, dict) and message.get(_ENVELOPE) == 1:
                        if message.get("origin") == self._origin:
                            continue  # this worker already delivered its own message
                        message = message.get("data")  # noqa: PLW2901
                    await self._deliver(self.members(room), message)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # the broadcaster (for example Redis) hiccuped: reconnect
                logger.warning(
                    "WebSocket room %r subscription lost (%s); retrying in %.1fs",
                    room,
                    type(exc).__name__,
                    delay,
                )
            await asyncio.sleep(delay)
            delay = min(delay * 2, _RECONNECT_MAX)

    async def close_broadcaster(self) -> None:
        """Stop cross-worker delivery and release the broadcaster's resources."""
        tasks = list(self._listeners.values())
        self._listeners.clear()
        self._pinned.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        broadcaster, self.broadcaster = self.broadcaster, None
        close = getattr(broadcaster, "close", None)
        if close is not None:
            with contextlib.suppress(Exception):
                await close()

    # ------------------------------------------------------------------------ shutdown

    async def close_all(self, code: int = GOING_AWAY, reason: str = "Server shutting down") -> None:
        """Close every open connection (so clients can reconnect) and stop cross-worker delivery."""
        sockets = tuple(self.connections)

        async def close(socket: Any) -> None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(socket.close(code, reason), 5.0)

        await asyncio.gather(*(close(s) for s in sockets))
        self.connections.clear()
        self.rooms.clear()
        self._memberships.clear()
        await self.close_broadcaster()
