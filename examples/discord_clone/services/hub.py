"""ChannelHub: the in-process half of realtime delivery.

Each Flaxon worker owns one ChannelHub. The hub:
- tracks which local WebSocket connections belong to which channel,
- keeps ephemeral presence and typing state (never persisted),
- subscribes to its Broadcaster and forwards inbound events to local sockets,
- publishes outbound events so OTHER workers' hubs can deliver them too.

Durable messages are persisted by the caller (services.messages) BEFORE the
hub broadcasts them, so a missed WebSocket event is always recoverable from
``/api/channels/<id>/messages``. The hub only ever carries live traffic.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict

TYPING_TTL = 8.0


class ChannelHub:
    def __init__(self, broadcaster, *, typing_ttl: float = TYPING_TTL) -> None:
        self.broadcaster = broadcaster
        self.typing_ttl = typing_ttl
        self._local: dict[int, set] = defaultdict(set)        # channel_id -> {socket}
        self._meta: dict = {}                                  # socket -> (channel_id, user_id)
        self._presence: dict[int, dict[int, int]] = defaultdict(dict)  # channel -> {user: count}
        self._typing: dict[int, dict[int, float]] = defaultdict(dict)  # channel -> {user: expiry}
        self._listeners: dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._sweeper: asyncio.Task | None = None

    # -- connection lifecycle ------------------------------------------------ #
    async def attach(self, socket, channel_id: int, user_id: int) -> None:
        async with self._lock:
            self._local[channel_id].add(socket)
            self._meta[socket] = (channel_id, user_id)
            entry = self._presence[channel_id]
            entry[user_id] = entry.get(user_id, 0) + 1
            if channel_id not in self._listeners or self._listeners[channel_id].done():
                self._listeners[channel_id] = asyncio.create_task(self._listen(channel_id))
                # Yield once so the listener subscribes BEFORE we publish.
                # Without this, an "immediate message" right after connect could
                # be published before this hub is listening and be lost.
                await asyncio.sleep(0)
        await self._publish_presence(channel_id)

    async def detach(self, socket) -> None:
        meta = self._meta.pop(socket, None)
        if meta is None:
            return
        channel_id, user_id = meta
        async with self._lock:
            self._local[channel_id].discard(socket)
            entry = self._presence[channel_id]
            remaining = entry.get(user_id, 0) - 1
            if remaining <= 0:
                entry.pop(user_id, None)
            else:
                entry[user_id] = remaining
            if not self._local[channel_id]:
                entry.clear()
                task = self._listeners.pop(channel_id, None)
                if task is not None:
                    task.cancel()
        await self._publish_presence(channel_id)

    # -- outbound ----------------------------------------------------------- #
    async def broadcast(self, channel_id: int, event: dict) -> None:
        """Publish an event so every worker (including this one) can deliver it."""
        await self.broadcaster.publish(str(channel_id), event)

    async def publish_typing(self, channel_id: int, user_id: int) -> None:
        self._typing[channel_id][user_id] = time.monotonic() + self.typing_ttl
        await self.broadcast(channel_id, {
            "type": "typing.update",
            "channel_id": channel_id,
            "user_ids": list(self._typing[channel_id].keys()),
        })

    async def _publish_presence(self, channel_id: int) -> None:
        user_ids = sorted(self._presence.get(channel_id, {}).keys())
        await self.broadcast(channel_id, {
            "type": "presence.update",
            "channel_id": channel_id,
            "user_ids": user_ids,
        })

    # -- inbound from broadcaster ------------------------------------------- #
    async def _listen(self, channel_id: int) -> None:
        backoff = 0.2
        while True:
            try:
                async for message in self.broadcaster.subscribe(str(channel_id)):
                    await self._deliver_local(channel_id, message)
                # Generator ended (broadcaster closed) — stop cleanly.
                break
            except asyncio.CancelledError:
                raise
            except Exception:
                # Transient broadcaster failure (e.g. Redis dropped the
                # connection). Back off and resubscribe unless the channel is
                # now empty, in which case the attach/detach bookkeeping owns it.
                async with self._lock:
                    if not self._local.get(channel_id):
                        break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 5.0)

    async def _deliver_local(self, channel_id: int, event: dict) -> None:
        sockets = list(self._local.get(channel_id, ()))
        for sock in sockets:
            try:
                await sock.send_json(event)
            except Exception:
                # A dead socket must not stall the loop; reap it on next tick.
                asyncio.create_task(self._safe_detach(sock))

    async def _safe_detach(self, socket) -> None:
        try:
            await self.detach(socket)
        except Exception:
            pass

    # -- queries ------------------------------------------------------------ #
    def presence_list(self, channel_id: int) -> list[int]:
        return sorted(self._presence.get(channel_id, {}).keys())

    def typing_list(self, channel_id: int) -> list[int]:
        now = time.monotonic()
        return [uid for uid, exp in self._typing.get(channel_id, {}).items() if exp > now]

    # -- background sweeper ------------------------------------------------- #
    async def start(self) -> None:
        if self._sweeper is None or self._sweeper.done():
            self._sweeper = asyncio.create_task(self._sweep())

    async def _sweep(self) -> None:
        while True:
            await asyncio.sleep(2.0)
            now = time.monotonic()
            for channel_id, users in list(self._typing.items()):
                expired = [uid for uid, exp in users.items() if exp <= now]
                if expired:
                    for uid in expired:
                        users.pop(uid, None)
                    await self.broadcast(channel_id, {
                        "type": "typing.update",
                        "channel_id": channel_id,
                        "user_ids": list(users.keys()),
                    })

    async def shutdown(self) -> None:
        for task in self._listeners.values():
            task.cancel()
        self._listeners.clear()
        if self._sweeper is not None:
            self._sweeper.cancel()
        await self.broadcaster.close()
