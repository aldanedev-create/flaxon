"""Shared pytest fixtures for the Discord-clone example tests.

Two notes that bit during development and are worth remembering:

1. Migrations run in a *subprocess*. Importing ``app`` builds the full (non-
   management) app, and Flaxon's ``configure_admin`` queries the admin store at
   construction — so the app's tables must already exist. Running migrate
   in-process would also cache the management-mode app (no routes) in
   sys.modules, which is why we shell out instead.

2. The Flaxon TestClient does not keep cookies between requests. Real browsers
   do, so ``SessionClient`` carries the session cookie (and CSRF token) for us.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# aiosqlite's per-connection worker thread is created without daemon=True, so
# Python's interpreter shutdown joins it forever unless the connection is
# explicitly closed (which the admin store's ORM facade never is in-process).
# The synchronous Admin store owns its own daemon loop thread, but its aiosqlite
# worker is not daemon and leaks across every test, deadlocking pytest at exit.
# Marking these threads daemon lets the process exit cleanly; it does not change
# runtime behaviour, only interpreter-shutdown waiting.
import aiosqlite.core as _aiosqlite_core

_aiosqlite_Connection_init = _aiosqlite_core.Connection.__init__


def _daemon_aiosqlite_connection_init(self, *args, **kwargs):
    _aiosqlite_Connection_init(self, *args, **kwargs)
    if getattr(self, "_thread", None) is not None:
        self._thread.daemon = True


_aiosqlite_core.Connection.__init__ = _daemon_aiosqlite_connection_init

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


def _db_path() -> str:
    return tempfile.mktemp(dir=str(DATA), suffix=".sqlite3")


@pytest.fixture(scope="session", autouse=True)
def _configure_and_migrate():
    os.environ["DATABASE_URL"] = "sqlite://" + _db_path()
    os.environ["FLAXON_SECRET_KEY"] = "test-secret-key-please-rotate-0123456789"
    os.environ["FLAXON_DEBUG"] = "true"
    os.environ["REDIS_URL"] = ""  # force the in-process MemoryBroadcaster
    os.environ["RATE_LIMIT_ENABLED"] = "false"  # tests share one client IP
    subprocess.run([sys.executable, "management.py", "migrate"], cwd=str(ROOT), check=True)
    yield


@pytest.fixture()
def app():
    from app import app as application

    asyncio.run(_initialize(application))
    yield application
    asyncio.run(_close(application))


async def _initialize(application):
    with application.db.bind():
        await application.db.initialize()


async def _close(application):
    with application.db.bind():
        await application.db.close()


@pytest.fixture(autouse=True)
def _clean_db(app):
    yield
    _truncate(app)


def _truncate(app) -> None:
    async def _go():
        from models import (
            Bot,
            BotMembership,
            BotToken,
            Channel,
            ChannelAccess,
            CommandInvocation,
            EventDelivery,
            EventSubscription,
            Membership,
            Message,
            Role,
            Server,
            SlashCommand,
            User,
        )

        # Delete children before parents to respect FK relationships.
        for model in (
            ChannelAccess,
            Message,
            Membership,
            BotMembership,
            EventDelivery,
            CommandInvocation,
            SlashCommand,
            EventSubscription,
            BotToken,
            Channel,
            Role,
            Bot,
            Server,
            User,
        ):
            await model.all().delete()

    with app.db.bind():
        asyncio.run(_go())


class SessionClient:
    """Cookie- and CSRF-aware wrapper around the synchronous Flaxon TestClient."""

    def __init__(self, app) -> None:
        from flaxon.testing import TestClient

        self.client = TestClient(app)
        self.cookies: dict[str, str] = {}
        self.csrf: str | None = None

    # -- low level -------------------------------------------------------- #
    def _headers(self, extra):
        headers = dict(extra or {})
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if self.csrf and "x-csrf-token" not in headers:
            headers["x-csrf-token"] = self.csrf
        return headers

    def _save(self, response) -> None:
        sc = response.headers.get("set-cookie")
        if sc:
            name, _, value = sc.split(";", 1)[0].partition("=")
            self.cookies[name.strip()] = value.strip()

    def _request(self, method, path, **kw):
        # The SPA fetches a CSRF token on startup; mirror that by grabbing one
        # lazily before the first state-changing request if we don't have one.
        if method in ("post", "patch", "delete") and self.csrf is None:
            self.fetch_csrf()
        headers = self._headers(kw.pop("headers", None))
        r = getattr(self.client, method)(path, headers=headers, **kw)
        self._save(r)
        return r

    # -- convenience ------------------------------------------------------ #
    def get(self, path, **kw):
        return self._request("get", path, **kw)

    def post(self, path, **kw):
        return self._request("post", path, **kw)

    def patch(self, path, **kw):
        return self._request("patch", path, **kw)

    def delete(self, path, **kw):
        return self._request("delete", path, **kw)

    def register(self, username, email, password):
        return self.post(
            "/api/auth/register",
            json_data={"username": username, "email": email, "password": password},
        )

    def login(self, username, password):
        return self.post("/api/auth/login", json_data={"username": username, "password": password})

    def fetch_csrf(self) -> str:
        self.csrf = self.get("/api/auth/csrf-token").json()["token"]
        return self.csrf


@pytest.fixture()
def client(app):
    return SessionClient(app)


@pytest.fixture()
def make_session(app):
    """Factory for an independent, cookie-isolated session against the same app."""
    def _factory() -> SessionClient:
        return SessionClient(app)

    return _factory
