"""Backend and callback failures should remain observable and bounded."""

import asyncio
import gzip
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from flaxon.exceptions import BadRequest
from flaxon.files.adapters.s3 import S3StorageAdapter
from flaxon.graphql.extensions.persisted_queries import PersistedQueriesExtension
from flaxon.http.body import BodyDecoder
from flaxon.tasks.registry import TaskRegistry
from flaxon.tasks.signals import Signal, SignalHandler
from flaxon.tasks.worker import Worker


@pytest.mark.asyncio
async def test_signal_failures_are_logged_and_other_listeners_continue(caplog):
    handler = SignalHandler()
    calls = []

    def failing():
        raise RuntimeError("Listener failed")

    async def async_failing():
        raise ValueError("Async listener failed")

    handler.connect(Signal.POST_RUN, failing)
    handler.connect(Signal.POST_RUN, async_failing)
    handler.connect(Signal.POST_RUN, lambda: calls.append("success"))
    await handler.emit(Signal.POST_RUN)
    assert calls == ["success"]
    assert sum("Task signal listener failed" in r.message for r in caplog.records) == 2
    assert all(r.exc_info for r in caplog.records)


@pytest.mark.asyncio
async def test_signal_cancellation_propagates():
    handler = SignalHandler()

    async def cancel():
        raise asyncio.CancelledError

    handler.connect(Signal.PRE_RUN, cancel)
    with pytest.raises(asyncio.CancelledError):
        await handler.emit(Signal.PRE_RUN)


@pytest.mark.asyncio
async def test_worker_backend_failures_back_off_cap_and_reset(monkeypatch, caplog):
    queue = SimpleNamespace(
        pop=AsyncMock(
            side_effect=[
                *[RuntimeError("Queue unavailable") for _ in range(8)],
                None,
                RuntimeError("Queue unavailable again"),
                asyncio.CancelledError(),
            ]
        )
    )
    worker = Worker(TaskRegistry(), queue=queue)
    worker._running = True
    delays = []

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("flaxon.tasks.worker.asyncio.sleep", sleep)
    await worker._worker_loop()
    assert delays == pytest.approx([0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 5, 5, 0.1])
    assert sum("Task worker iteration failed" in r.message for r in caplog.records) == 9


@pytest.mark.asyncio
async def test_worker_cancellation_during_backoff_propagates(monkeypatch):
    queue = SimpleNamespace(pop=AsyncMock(side_effect=RuntimeError("Unavailable")))
    worker = Worker(TaskRegistry(), queue=queue)
    worker._running = True

    async def cancel(delay):
        raise asyncio.CancelledError

    monkeypatch.setattr("flaxon.tasks.worker.asyncio.sleep", cancel)
    with pytest.raises(asyncio.CancelledError):
        await worker._worker_loop()


@pytest.fixture
def s3_error_type(monkeypatch):
    # Exercise the adapter without requiring the optional AWS dependency.
    module = ModuleType("botocore.exceptions")

    class ClientError(Exception):
        def __init__(self, code):
            self.response = {"Error": {"Code": code}}

    module.ClientError = ClientError
    monkeypatch.setitem(sys.modules, "botocore.exceptions", module)
    return ClientError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code, missing",
    [("404", True), ("NoSuchKey", True), ("NotFound", True), ("AccessDenied", False), ("500", False)],
)
async def test_s3_exists_only_returns_false_for_missing_objects(s3_error_type, code, missing):
    adapter = S3StorageAdapter("test")
    error = s3_error_type(code)
    client = SimpleNamespace(head_object=AsyncMock(side_effect=error))
    context = AsyncMock()
    context.__aenter__.return_value = client
    adapter._client = SimpleNamespace(client=lambda *args, **kwargs: context)
    if missing:
        assert await adapter.exists("document") is False
    else:
        with pytest.raises(s3_error_type) as captured:
            await adapter.exists("document")
        assert captured.value is error


@pytest.mark.asyncio
async def test_s3_unexpected_failure_propagates_and_existing_object_is_true(s3_error_type):
    adapter = S3StorageAdapter("test")
    client = SimpleNamespace(head_object=AsyncMock())
    context = AsyncMock()
    context.__aenter__.return_value = client
    adapter._client = SimpleNamespace(client=lambda *args, **kwargs: context)
    assert await adapter.exists("document") is True
    client.head_object.side_effect = RuntimeError("Client bug")
    with pytest.raises(RuntimeError, match="Client bug"):
        await adapter.exists("document")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "encoding, data", [("gzip", b"bad"), ("gzip", gzip.compress(b"ok")[:-3]), ("deflate", b"bad")]
)
async def test_invalid_compressed_body_remains_bad_request(encoding, data):
    with pytest.raises(BadRequest):
        await BodyDecoder.decode(SimpleNamespace(headers={"content-encoding": encoding}), data)


@pytest.mark.asyncio
async def test_body_decoder_does_not_hide_programming_errors(monkeypatch):
    def fail(data):
        raise RuntimeError("Decoder bug")

    monkeypatch.setattr(gzip, "decompress", fail)
    with pytest.raises(RuntimeError, match="Decoder bug"):
        await BodyDecoder.decode(SimpleNamespace(headers={"content-encoding": "gzip"}), b"data")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        [],
        None,
        {"extensions": []},
        {"extensions": {"persistedQuery": []}},
        {"extensions": {"persistedQuery": {"sha256Hash": []}}},
    ],
)
async def test_persisted_queries_ignore_malformed_shapes(data):
    extension = PersistedQueriesExtension()
    context = {"request": SimpleNamespace(json=AsyncMock(return_value=data))}
    await extension.before(context)
    assert "resolved_query" not in context


@pytest.mark.asyncio
async def test_persisted_queries_do_not_hide_request_failures():
    extension = PersistedQueriesExtension()
    context = {"request": SimpleNamespace(json=AsyncMock(side_effect=RuntimeError("Reader bug")))}
    with pytest.raises(RuntimeError, match="Reader bug"):
        await extension.before(context)
    context["request"].json.side_effect = json.JSONDecodeError("invalid", "", 0)
    await extension.before(context)
