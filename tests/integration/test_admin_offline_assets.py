"""Real-server check: the admin never asks a browser to fetch a CDN asset.

Runs a real uvicorn server and drives it with a real HTTP client (not the in-process
TestClient). This is the failure mode users hit in production: a page that renders only
because the browser can reach a third-party CDN.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
import uvicorn

from flaxon import Flaxon
from flaxon.admin import AdminDashboard

CDN_PATTERN = re.compile(
    r"https?://(?:cdn\.tailwindcss\.com|cdnjs\.cloudflare\.com|fonts\.googleapis\.com|"
    r"fonts\.gstatic\.com|unpkg\.com|cdn\.jsdelivr\.net)",
    re.IGNORECASE,
)


@pytest_asyncio.fixture
async def server(unused_tcp_port: int) -> AsyncIterator[int]:
    app = Flaxon("admin-offline", debug=True)
    AdminDashboard(app, users=[{"username": "admin", "password": "Admin123!"}])
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=unused_tcp_port,
        log_level="error",
        timeout_graceful_shutdown=1,
    )
    instance = uvicorn.Server(config)
    task = asyncio.create_task(instance.serve())
    for _ in range(100):
        if instance.started:
            break
        await asyncio.sleep(0.05)
    assert instance.started
    try:
        yield unused_tcp_port
    finally:
        instance.should_exit = True
        await task


@pytest.mark.asyncio
async def test_admin_login_page_has_no_cdn_and_serves_local_assets(server: int):
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{server}") as client:
        login = await client.get("/admin/login")
        assert login.status_code == 200
        assert not CDN_PATTERN.search(login.text), "login page references a CDN:\n" + "\n".join(
            line for line in login.text.splitlines() if CDN_PATTERN.search(line)
        )

        for path in (
            "/static/admin/vendor/tailwind/tailwind.min.css",
            "/static/admin/vendor/font-awesome/css/all.min.css",
            "/static/admin/vendor/font-awesome/webfonts/fa-solid-900.woff2",
            "/static/admin/vendor/inter/inter.css",
            "/static/admin/vendor/inter/files/inter-latin-400-normal.woff2",
        ):
            response = await client.get(path)
            assert response.status_code == 200, f"{path} -> {response.status_code}"
            assert len(response.content) > 0

        # The webfont path inside Font Awesome's CSS resolves relative to css/all.min.css.
        css = await client.get("/static/admin/vendor/font-awesome/css/all.min.css")
        assert "../webfonts/fa-solid-900.woff2" in css.text
