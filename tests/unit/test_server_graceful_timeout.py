"""ServerConfig.timeout_graceful_shutdown must reach uvicorn; POSIX signals stay put."""

from __future__ import annotations

import inspect
import sys
from types import SimpleNamespace

import pytest

import flaxon.server.processes as processes
import flaxon.server.production as production
from flaxon.server.configuration import ServerConfig
from flaxon.server.processes import WorkerProcess
from flaxon.server.production import ProductionServer


class _FakeServer:
    def __init__(self, config):
        self.config = config

    async def serve(self):
        return None

    async def shutdown(self):
        return None


class _FakeUvicorn:
    def __init__(self, seen: list[dict]):
        self.seen = seen

    def Config(self, app, **kwargs):  # noqa: N802 - mirrors uvicorn.Config
        self.seen.append(kwargs)
        return SimpleNamespace()

    def Server(self, config):  # noqa: N802
        return _FakeServer(config)


@pytest.mark.asyncio
async def test_single_worker_passes_graceful_timeout_to_uvicorn(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(production, "import_module", lambda name: _FakeUvicorn(seen))
    config = ServerConfig(host="127.0.0.1", port=8123, workers=1, timeout_graceful_shutdown=45)
    server = ProductionServer(config)
    await server.run_async(object())
    assert seen, "uvicorn.Config was not constructed"
    assert seen[0].get("timeout_graceful_shutdown") == 45


def test_worker_process_passes_graceful_timeout_to_uvicorn(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(processes, "import_module", lambda name: _FakeUvicorn(seen))
    config = SimpleNamespace(host="127.0.0.1", port=8123, log_level="info", timeout_graceful_shutdown=17)
    worker = WorkerProcess(0, object(), config)
    worker._run_worker(0, object(), config)
    assert seen and seen[0].get("timeout_graceful_shutdown") == 17


@pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM unavailable on Windows")
def test_single_worker_signal_handling_is_not_posix_only():
    """The POSIX-only add_signal_handler path is confined to the multi-worker branch."""
    source = inspect.getsource(ProductionServer.run_async)
    single_worker_branch = source.split("else:", 1)[-1]
    assert "add_signal_handler" not in single_worker_branch
