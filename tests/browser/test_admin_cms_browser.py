from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("playwright")
pytest.importorskip("uvicorn")

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.cms import CMS, CMSField, ContentType


@pytest.mark.asyncio
async def test_admin_login_and_cms_create_in_browser(unused_tcp_port):
    from playwright.async_api import async_playwright
    import uvicorn

    app = Flaxon("browser-admin", debug=True)
    AdminDashboard(app, users=[{"username": "admin", "password": "Admin123!"}])
    cms = CMS(app)
    cms.register(ContentType("post", fields=[CMSField("title", required=True)]))
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=unused_tcp_port,
            log_level="error",
            timeout_graceful_shutdown=1,
        )
    )
    browser = None
    task = asyncio.create_task(server.serve())
    try:
        for _ in range(100):
            if server.started:
                break
            await asyncio.sleep(0.05)
        assert server.started
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, timeout=15000)
            page = await browser.new_page()
            page.set_default_timeout(15000)
            # Essential Admin JS is bundled; cosmetic CDNs are unnecessary for this test.
            await page.route("https://**/*", lambda route: route.abort())
            await page.goto(f"http://127.0.0.1:{unused_tcp_port}/admin/login")
            csrf = await page.locator('input[name="_csrf"]').input_value()
            assert csrf
            await page.locator('input[name="username"]').fill("admin")
            await page.locator('input[name="password"]').fill("Admin123!")
            await page.locator('form button').click()
            await page.wait_for_url(f"http://127.0.0.1:{unused_tcp_port}/admin/", wait_until="commit", timeout=15000)
            response = await page.goto(f"http://127.0.0.1:{unused_tcp_port}/admin/cms/")
            await page.wait_for_function("() => typeof Alpine !== 'undefined'")
            assert response and response.ok
            assert await page.evaluate("() => window.FLAXON_CMS_API_BASE === '/admin/cms/api'")
            await page.get_by_label("CMS content navigation", exact=True).get_by_role("button", name="Posts", exact=True).click()
            await page.get_by_text("Add Post", exact=False).click()
            await page.locator('input[x-model="formData[f.name]"]').first.fill("Browser-created post")
            await page.get_by_text("Save", exact=True).click()
            await page.get_by_text("Browser-created post", exact=True).wait_for()
            await browser.close()
            browser = None
    finally:
        if browser is not None:
            await browser.close()
        server.should_exit = True
        server.force_exit = True
        await task
