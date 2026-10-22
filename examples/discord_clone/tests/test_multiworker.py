"""Multi-worker realtime (Phase 7): hubs talk only through the Broadcaster.

The whole point of the final phase: each Flaxon worker owns one ChannelHub, and
hubs never speak directly — they publish/subscribe through a Broadcaster. With
Redis in production, every hub shares one Redis-backed broadcaster, so a message
sent on worker A reaches a socket attached on worker B. In dev/tests we prove
the same property with a *single* in-process MemoryBroadcaster shared by two
hubs, and we prove the broken, naive case by giving each hub its own instance.
"""
from __future__ import annotations

import asyncio

from services.broadcaster import MemoryBroadcaster
from services.hub import ChannelHub


class FakeSocket:
    """Stand-in for a WebSocket: records every JSON frame pushed to it."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, event: dict) -> None:
        self.sent.append(event)


async def _shared_broadcaster() -> bool:
    broadcaster = MemoryBroadcaster()  # ONE instance, two hubs
    hub_a = ChannelHub(broadcaster)
    hub_b = ChannelHub(broadcaster)

    sock_b = FakeSocket()
    await hub_b.attach(sock_b, channel_id=1, user_id=2)
    await asyncio.sleep(0.05)  # let hub_b's listener subscribe to channel 1

    # worker A sends a message; it must reach the socket attached on worker B.
    await hub_a.broadcast(1, {"type": "message.create", "id": 42})
    await asyncio.sleep(0.1)

    crossed = any(m.get("id") == 42 for m in sock_b.sent)
    await hub_b.detach(sock_b)
    return crossed


async def _separate_broadcasters() -> bool:
    hub_a = ChannelHub(MemoryBroadcaster())  # each hub, its own instance
    hub_b = ChannelHub(MemoryBroadcaster())

    sock_b = FakeSocket()
    await hub_b.attach(sock_b, channel_id=1, user_id=2)
    await asyncio.sleep(0.05)
    await hub_a.broadcast(1, {"type": "message.create", "id": 7})
    await asyncio.sleep(0.1)

    got = any(m.get("id") == 7 for m in sock_b.sent)
    await hub_b.detach(sock_b)
    return got


def test_shared_broadcaster_delivers_cross_worker():
    # The correct topology: hubs share a broadcaster, so events cross workers.
    assert asyncio.run(_shared_broadcaster()) is True


def test_separate_broadcasters_do_not_deliver():
    # The naive, single-process mistake: isolated broadcasters drop the event.
    assert asyncio.run(_separate_broadcasters()) is False
