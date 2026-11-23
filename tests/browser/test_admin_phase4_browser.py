"""Phase 4 acceptance in a real browser: filters, lenses, palette, duplicate,
and impersonation against a seeded Tortoise/SQLite database.

Boots the real ASGI app under uvicorn, logs in through the real form, and drives
the UI in Chromium. Screenshots are captured from the running app (written to a
docs directory when FLAXON_DOCS_SCREENSHOT_DIR is set).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.filters import BooleanFilter, SelectFilter
from flaxon.admin.lenses import Lens


@pytest.mark.timeout(240)
def test_phase4_ui_in_real_browser(tmp_path):
    pytest.importorskip("playwright.async_api")
    import uvicorn  # noqa: PLC0415 - optional test dependency
    from playwright.async_api import async_playwright  # noqa: PLC0415 - optional test dependency
    from tortoise import Model, Tortoise, fields  # noqa: PLC0415 - optional test dependency

    module = ModuleType("browser_phase4_models")
    sys.modules["browser_phase4_models"] = module

    class Order(Model):
        reference = fields.CharField(max_length=50)
        status = fields.CharField(max_length=20)
        fulfilled = fields.BooleanField(default=False)

        class Meta:
            app = "browser_phase4_models"
            table = "browser_phase4_order"

    Order.__module__ = "browser_phase4_models"
    module.Order = Order

    async def scenario():
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"browser_phase4_models": ["browser_phase4_models"]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas()
        for index, (status, fulfilled) in enumerate([
            ("pending", False),
            ("paid", True),
            ("paid", False),
            ("pending", True),
        ]):
            await Order.create(reference=f"ORD-{index}", status=status, fulfilled=fulfilled)

        app = Flaxon("phase4-browser")
        dashboard = AdminDashboard(
            app,
            config=AdminConfig(allow_impersonation=True),
            users=[
                {
                    "username": "admin",
                    "password": "Admin123!",
                    "permissions": ["admin.superuser", "admin.impersonate"],
                },
                {
                    "username": "viewer",
                    "password": "Viewer123!",
                    "permissions": ["admin.view_dashboard", "order.view_order"],
                },
            ],
            upload_dir=str(tmp_path / "uploads"),
            storage_path=str(tmp_path / "admin.sqlite3"),
        )
        dashboard.register(
            Order,
            list_display=["reference", "status", "fulfilled"],
            fields=["reference", "status", "fulfilled"],
            filters=[
                SelectFilter("status", choices=["pending", "paid"], label="Status"),
                BooleanFilter("fulfilled", label="Fulfilled"),
            ],
            lenses=[
                Lens(
                    "unpaid",
                    label="Unpaid orders",
                    columns=["reference", "status"],
                    query={"filter_status": "pending"},
                ),
            ],
        )

        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())
        for _ in range(120):
            if server.started:
                break
            await asyncio.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        shot_dir = Path(os.environ.get("FLAXON_DOCS_SCREENSHOT_DIR") or tmp_path)
        shot_dir.mkdir(parents=True, exist_ok=True)
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1400, "height": 1000})
                await page.goto(f"{origin}/admin/login")
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "Admin123!")
                await page.click("button.login-submit")
                await page.wait_for_url("**/admin/", timeout=15000)

                # --- Filters: class-based panel, state in the URL.
                await page.goto(f"{origin}/admin/order")
                assert await page.locator(".fx-filter-panel").count() == 1
                await page.select_option('select[name="filter_status"]', "paid")
                await page.click(".fx-filter-apply")
                await page.wait_for_load_state("networkidle")
                assert "filter_status=paid" in page.url, page.url
                rows = await page.locator("table tbody tr").all_text_contents()
                assert len(rows) == 2, rows
                assert all("paid" in row for row in rows), rows

                await page.screenshot(path=str(shot_dir / "admin-filters.png"), full_page=True)

                # --- Lenses: alternate query and columns.
                await page.click('.fx-lens:has-text("Unpaid orders")')
                await page.wait_for_load_state("networkidle")
                assert "lens=unpaid" in page.url, page.url
                rows = await page.locator("table tbody tr").all_text_contents()
                assert len(rows) == 2, rows
                assert all("pending" in row for row in rows), rows
                assert await page.locator(".fx-lens.is-active").inner_text() == "Unpaid orders"

                # --- Command palette: Ctrl/Cmd+K, type, Escape.
                await page.keyboard.press("Control+k")
                await page.wait_for_selector("#fx-palette:not([hidden])", timeout=5000)
                await page.fill("#fx-palette-input", "ORD-2")
                await page.wait_for_function(
                    "document.querySelectorAll('#fx-palette-results li').length > 0", timeout=5000
                )
                results = await page.locator("#fx-palette-results li").all_text_contents()
                assert any("ORD-2" in text for text in results), results
                await page.screenshot(path=str(shot_dir / "admin-palette.png"), full_page=False)
                await page.keyboard.press("Escape")
                await page.wait_for_selector("#fx-palette[hidden]", state="attached", timeout=5000)

                # --- Duplicate: a real new row in the database.
                before = await Order.all().count()
                await page.goto(f"{origin}/admin/order")
                await page.locator('button[aria-label="Duplicate"]').first.click()
                await page.wait_for_load_state("networkidle")
                after = await Order.all().count()
                assert after == before + 1, (before, after)

                # --- Impersonation: banner, one-click exit, audit trail.
                token = await page.locator('input[name="_csrf"]').first.get_attribute("value")
                started = await page.evaluate(
                    """async (csrf) => {
                        const body = new URLSearchParams({ _csrf: csrf, username: 'viewer' });
                        const response = await fetch('/admin/impersonate', {
                            method: 'POST', body, credentials: 'same-origin',
                        });
                        return response.status;
                    }""",
                    token,
                )
                assert started == 200, started
                await page.goto(f"{origin}/admin/")
                banner = page.locator("[data-impersonation-banner]")
                await banner.wait_for(timeout=5000)
                assert "viewer" in (await banner.inner_text())

                await page.click(".fx-impersonation-exit button")
                await page.wait_for_load_state("networkidle")
                assert await page.locator("[data-impersonation-banner]").count() == 0

                actions = [entry.get("action") for entry in dashboard.store.get("audit", "entries", [])]
                assert "impersonation_started" in actions
                assert "impersonation_stopped" in actions

                await browser.close()
        finally:
            await Tortoise.close_connections()
            sys.modules.pop("browser_phase4_models", None)
            server.should_exit = True
            await task

    asyncio.run(scenario())
