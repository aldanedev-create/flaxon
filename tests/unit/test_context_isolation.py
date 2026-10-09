"""Context helpers must not mutate values shared by independent async requests."""

import asyncio
import contextvars
import logging

import pytest

from flaxon.application.context import get_request_context, request_context
from flaxon.dependency_injection.scope import Scope
from flaxon.logging.configuration import LoggingConfig
from flaxon.logging.context import LogContext, LogContextMiddleware, get_log_context, set_log_context
from flaxon.logging.handlers import RotatingFileHandler
from flaxon.tasks.context import TaskContext


@pytest.mark.parametrize(
    "setter, getter",
    [
        (
            lambda key, value: get_request_context().set(key, value),
            lambda key: get_request_context().get(key),
        ),
        (set_log_context, get_log_context),
        (Scope.set_data, Scope.get_data),
        (TaskContext.set_data, TaskContext.get_data),
    ],
)
def test_fresh_contexts_have_independent_storage(setter, getter):
    first, second = contextvars.Context(), contextvars.Context()
    first.run(setter, "user", "alice")
    assert first.run(getter, "user") == "alice"
    assert second.run(getter, "user") is None
    second.run(setter, "user", "bob")
    assert first.run(getter, "user") == "alice"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setter, getter",
    [
        (
            lambda key, value: get_request_context().set(key, value),
            lambda key: get_request_context().get(key),
        ),
        (set_log_context, get_log_context),
        (Scope.set_data, Scope.get_data),
        (TaskContext.set_data, TaskContext.get_data),
    ],
)
async def test_child_tasks_copy_context_on_write(setter, getter):
    setter("user", "parent")
    ready = asyncio.Event()
    count = 0

    async def child(name):
        nonlocal count
        assert getter("user") == "parent"
        setter("user", name)
        count += 1
        if count == 2:
            ready.set()
        await ready.wait()
        assert getter("user") == name

    await asyncio.gather(child("alice"), child("bob"))
    assert getter("user") == "parent"


def test_request_context_facades_share_current_scope_and_restore_outer_values():
    def verify():
        outer = get_request_context()
        outer["value"] = "outer"
        with request_context(None):
            first, second = get_request_context(), get_request_context()
            first["value"] = "inner"
            assert second["value"] == "inner"
            del second["value"]
            assert first.get("value") is None
        assert outer["value"] == "outer"

    contextvars.Context().run(verify)


@pytest.mark.asyncio
async def test_log_context_middleware_restores_fields_and_isolates_requests():
    set_log_context("request_id", "outer")
    seen = []
    arrived = 0
    ready = asyncio.Event()

    async def app(scope, receive, send):
        nonlocal arrived
        assert get_log_context("request_id") == scope["flaxon.request_id"]
        set_log_context("user", scope["user"])
        arrived += 1
        if arrived == 2:
            ready.set()
        await ready.wait()
        seen.append((get_log_context("request_id"), get_log_context("user")))

    middleware = LogContextMiddleware(app)
    await asyncio.gather(*[
        middleware({"type": "http", "flaxon.request_id": name, "user": name}, None, None)
        for name in ("alice", "bob")
    ])
    assert sorted(seen) == [("alice", "alice"), ("bob", "bob")]
    assert get_log_context("request_id") == "outer"
    assert get_log_context("user") is None


def test_nested_log_context_restores_parent_after_exception():
    def verify():
        context = LogContext()
        context.set("scope", "outer")
        with pytest.raises(RuntimeError), LogContext() as inner:
            inner.update({"scope": "inner"})
            raise RuntimeError("Fail inside scope")
        assert context.get("scope") == "outer"

    contextvars.Context().run(verify)


def test_logging_handler_configuration_copies_defaults_and_input(monkeypatch):
    monkeypatch.delenv("LOG_FILE", raising=False)
    first, second = LoggingConfig(), LoggingConfig()
    first.add_console_handler()
    assert second.handlers == []
    supplied = {"handlers": [{"type": "console"}]}
    config = LoggingConfig(supplied)
    config.handlers[0]["formatter"] = "json"
    config.add_file_handler("example.log")
    assert supplied == {"handlers": [{"type": "console"}]}
    monkeypatch.setenv("LOG_FILE", "flaxon.log")
    assert len(LoggingConfig().handlers) == len(LoggingConfig().handlers) == 1
    assert LoggingConfig.DEFAULTS["handlers"] == []


def test_rotating_handler_uses_size_backup_and_encoding_settings(tmp_path):
    path = tmp_path / "application.log"
    handler = RotatingFileHandler(str(path), max_bytes=64, backup_count=1, encoding="utf-8")
    try:
        assert handler.maxBytes == 64
        assert handler.backupCount == 1
        assert handler.encoding == "utf-8"
        for message in ["First record " + "x" * 40, "Second record " + "y" * 40]:
            handler.emit(logging.LogRecord("test", logging.INFO, "", 0, message, (), None))
    finally:
        handler.close()
    assert "Second record" in path.read_text()
    assert "First record" in path.with_suffix(".log.1").read_text()
