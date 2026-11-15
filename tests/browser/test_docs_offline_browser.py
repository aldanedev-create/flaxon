"""/docs (Swagger UI) and /redoc must render in a real browser with no internet access at all."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import pytest
import pytest_asyncio

pytest.importorskip("playwright")
pytest.importorskip("uvicorn")

import uvicorn
from playwright.async_api import async_playwright

from flaxon import Flaxon

# ReDoc's footer ("API docs by Redocly") links a decorative logo from its own CDN. It is the only
# third-party request either page makes, and ReDoc renders fine when it fails.
DECORATIVE = {"https://cdn.redoc.ly/redoc/logo-mini.svg"}
# A host that is not localhost, so the page behaves as it would on a real public deployment.
PUBLIC_HOST = "docs.example.test"


@pytest_asyncio.fixture
async def server(unused_tcp_port: int) -> AsyncIterator[int]:
    app = Flaxon("offline-docs", openapi={"title": "Offline Docs", "version": "9.9.9"})

    @app.get("/widgets/<int:widget_id>")
    async def read_widget(widget_id: int):
        return {"id": widget_id}

    config = uvicorn.Config(
        app, host="127.0.0.1", port=unused_tcp_port, log_level="error", timeout_graceful_shutdown=1
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


async def open_offline(port: int, path: str):
    """Open a page with every request to a non-local host aborted; return (urls, blocked, errors, close)."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True, timeout=15000, args=[f"--host-resolver-rules=MAP {PUBLIC_HOST} 127.0.0.1"]
    )
    page = await browser.new_page()
    page.set_default_timeout(15000)
    local: list[str] = []
    blocked: list[str] = []
    errors: list[str] = []

    async def only_local(route):
        if urlparse(route.request.url).hostname == PUBLIC_HOST:
            local.append(route.request.url)
            await route.continue_()
        else:
            blocked.append(route.request.url)
            await route.abort()

    async def close() -> None:
        await browser.close()
        await playwright.stop()

    await page.route("**/*", only_local)
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(f"http://{PUBLIC_HOST}:{port}{path}")
    return page, local, blocked, errors, close


@pytest.mark.asyncio
async def test_swagger_ui_renders_offline_with_no_third_party_requests(server):
    page, local, blocked, errors, close = await open_offline(server, "/docs")
    try:
        await page.get_by_role("heading", name="Offline Docs").first.wait_for()
        await page.locator(".opblock-summary-path", has_text="/widgets/{widget_id}").wait_for()
        await asyncio.sleep(1)  # give a validator badge or any late request time to fire
    finally:
        await close()
    assert not errors, errors
    assert any("/docs/assets/" in url and url.endswith("swagger-ui-bundle.js") for url in local)
    assert any(url.endswith("swagger-ui.css") for url in local)
    assert not blocked, f"third-party requests: {blocked}"


@pytest.mark.asyncio
async def test_redoc_renders_offline_from_the_bundled_script(server):
    page, local, blocked, errors, close = await open_offline(server, "/redoc")
    try:
        await page.get_by_role("heading", name="Offline Docs").first.wait_for()
        await page.get_by_role("menuitem", name="read_widget").first.wait_for()
        assert await page.get_by_text("widget_id").first.is_visible()
    finally:
        await close()
    assert not errors, errors
    assert any("/redoc/redoc.standalone.js" in url for url in local)
    unexpected = sorted(set(blocked) - DECORATIVE)
    assert not unexpected, f"unexpected third-party requests: {unexpected}"
