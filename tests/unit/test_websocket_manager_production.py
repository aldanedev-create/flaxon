"""WebSocketManager under the failures production produces: dead peers, slow peers, outages."""

from __future__ import annotations

import asyncio
import time

import pytest

from flaxon.websocket import WebSocketManager
from flaxon.websocket.broadcaster import MemoryBroadcaster


class FakeSocket:
    def __init__(self, *, fail: bool = False, delay: float = 0.0) -> None:
        self.fail, self.delay = fail, delay
        self.received: list = []
        self.closed: tuple | None = None

    async def send_json(self, value) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise ConnectionError("peer is gone")
        self.received.append(value)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = (code, reason)


async def settle(seconds: float = 0.1) -> None:
    await asyncio.sleep(seconds)


@pytest.mark.asyncio
async def test_one_dead_peer_does_not_stop_the_broadcast_or_crash_the_sender():
    manager = WebSocketManager()
    healthy = [FakeSocket() for _ in range(25)]
    dead = FakeSocket(fail=True)
    for socket in [*healthy, dead]:
        await manager.join("room", socket)
    await manager.broadcast_json("room", {"n": 1})  # must not raise
    assert all(socket.received == [{"n": 1}] for socket in healthy)
    assert dead not in manager.members("room"), "the dead peer is evicted"


@pytest.mark.asyncio
async def test_slow_peers_are_delivered_to_concurrently_and_dropped_after_the_timeout():
    manager = WebSocketManager(send_timeout=0.3)
    slow = [FakeSocket(delay=0.2) for _ in range(5)]
    for socket in slow:
        await manager.join("room", socket)
    started = time.perf_counter()
    await manager.broadcast_json("room", 1)
    assert time.perf_counter() - started < 0.5, "five 0.2s peers must not take a serial one second"

    stuck = FakeSocket(delay=30)
    await manager.join("room", stuck)
    await manager.broadcast_json("room", 2)
    assert stuck not in manager.members("room")
    assert stuck.closed is not None and stuck.closed[0] == 1013


@pytest.mark.asyncio
async def test_rooms_do_not_leak_memory():
    manager = WebSocketManager()
    socket = FakeSocket()
    for index in range(200):
        await manager.leave(f"never-joined-{index}", socket)
        await manager.join(f"room-{index}", socket)
        await manager.leave(f"room-{index}", socket)
    assert manager.rooms == {} and manager._memberships == {}

    for index in range(50):
        await manager.join(f"room-{index}", socket)
    await manager.disconnect(socket)
    await manager.disconnect(socket)  # idempotent
    assert manager.rooms == {} and manager.connections == set() and manager._memberships == {}


@pytest.mark.asyncio
async def test_connection_limit_and_capacity():
    manager = WebSocketManager(max_connections=2)
    first, second = FakeSocket(), FakeSocket()
    assert manager.has_capacity
    await manager.connect(first)
    await manager.connect(second)
    assert not manager.has_capacity
    await manager.disconnect(first)
    assert manager.has_capacity


@pytest.mark.asyncio
async def test_close_all_closes_every_connection_and_clears_state():
    manager = WebSocketManager()
    sockets = [FakeSocket() for _ in range(3)]
    for socket in sockets:
        await manager.connect(socket)
        await manager.join("room", socket)
    await manager.close_all()
    assert all(socket.closed == (1001, "Server shutting down") for socket in sockets)
    assert manager.connections == set() and manager.rooms == {}


# --- sharing rooms between workers ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_failing_peer_does_not_kill_the_cross_worker_listener():
    broadcaster = MemoryBroadcaster()
    manager = WebSocketManager()
    healthy, dead = FakeSocket(), FakeSocket(fail=True)
    await manager.join("room", healthy)
    await manager.join("room", dead)
    await manager.configure_broadcaster(broadcaster)
    await settle()
    for number in (1, 2):
        await broadcaster.publish("room", {"__flaxon_ws__": 1, "origin": "other-worker", "data": number})
        await settle()
    assert healthy.received == [1, 2]
    assert not manager._listeners["room"].done()
    await manager.close_broadcaster()


@pytest.mark.asyncio
async def test_rooms_joined_after_configuration_still_receive_other_workers_messages():
    broadcaster = MemoryBroadcaster()
    manager = WebSocketManager()
    await manager.configure_broadcaster(broadcaster)
    late = FakeSocket()
    await manager.join("late-room", late)
    await settle()
    await broadcaster.publish("late-room", {"__flaxon_ws__": 1, "origin": "other-worker", "data": "hello"})
    await settle()
    assert late.received == ["hello"]
    await manager.close_broadcaster()


@pytest.mark.asyncio
async def test_a_message_sent_right_after_joining_is_delivered_once_locally():
    manager = WebSocketManager()
    await manager.configure_broadcaster(MemoryBroadcaster())
    socket = FakeSocket()
    await manager.join("room", socket)
    await manager.broadcast_json("room", {"n": 1})  # no waiting for the subscription to exist
    await settle()
    assert socket.received == [{"n": 1}]
    await manager.close_broadcaster()


@pytest.mark.asyncio
async def test_two_workers_each_deliver_once_and_never_echo_their_own_messages():
    shared = MemoryBroadcaster()
    worker_a, worker_b = WebSocketManager(), WebSocketManager()
    a_peer, b_peer = FakeSocket(), FakeSocket()
    await worker_a.join("room", a_peer)
    await worker_b.join("room", b_peer)
    await worker_a.configure_broadcaster(shared)
    await worker_b.configure_broadcaster(shared)
    await settle()
    await worker_a.broadcast_json("room", "from-a")
    await worker_b.broadcast_json("room", "from-b")
    await settle(0.2)
    assert sorted(a_peer.received) == ["from-a", "from-b"]
    assert sorted(b_peer.received) == ["from-a", "from-b"]
    await worker_a.close_broadcaster()
    await worker_b.close_broadcaster()


@pytest.mark.asyncio
async def test_a_broadcaster_outage_degrades_gracefully_instead_of_crashing_the_sender():
    class Down(MemoryBroadcaster):
        async def publish(self, channel, message):
            raise ConnectionError("redis is down")

    manager = WebSocketManager(Down())
    socket = FakeSocket()
    await manager.join("room", socket)
    await manager.broadcast_json("room", {"n": 1})  # must not raise
    assert socket.received == [{"n": 1}]
    await manager.close_broadcaster()


@pytest.mark.asyncio
async def test_the_listener_resubscribes_after_the_broadcaster_fails():
    class Flaky(MemoryBroadcaster):
        attempts = 0

        async def subscribe(self, channel):
            type(self).attempts += 1
            if type(self).attempts == 1:
                raise ConnectionError("connection lost")
            async for message in super().subscribe(channel):
                yield message

    broadcaster = Flaky()
    manager = WebSocketManager()
    socket = FakeSocket()
    await manager.join("room", socket)
    await manager.configure_broadcaster(broadcaster)
    await asyncio.sleep(0.9)  # first attempt fails, the retry after 0.5s succeeds
    await broadcaster.publish("room", {"__flaxon_ws__": 1, "origin": "other-worker", "data": "back"})
    await settle()
    assert Flaky.attempts == 2 and socket.received == ["back"]
    await manager.close_broadcaster()


@pytest.mark.asyncio
async def test_memory_broadcaster_keeps_only_the_newest_messages_for_a_stalled_subscriber():
    broadcaster = MemoryBroadcaster(queue_size=3)
    received: list = []
    gate = asyncio.Event()

    async def consume() -> None:
        async for message in broadcaster.subscribe("room"):
            received.append(message)
            if len(received) == 1:
                await gate.wait()  # stall after the first message
            if len(received) == 4:
                return

    task = asyncio.create_task(consume())
    await settle()
    await broadcaster.publish("room", 0)
    await settle()  # the consumer takes 0, then stalls
    for number in range(1, 10):
        await broadcaster.publish("room", number)  # only the newest 3 fit
    gate.set()
    await asyncio.wait_for(task, 2)
    assert received == [0, 7, 8, 9]
