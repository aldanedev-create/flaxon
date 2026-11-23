"""Phase 5 acceptance in a real browser: a Teloce field, card and page.

Boots uvicorn with a seeded SQLite database, installs the example extension,
logs in through the real form, and drives Chromium. The screenshot is written to
``FLAXON_DOCS_SCREENSHOT_DIR`` when that variable is set.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import ClassVar

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.resources import Field, Resource, Text

PLUGIN_ROOT = str(Path(__file__).parents[2] / "examples" / "flaxon_admin_rating")
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from flaxon_admin_rating import RatingExtension, RatingField  # noqa: E402


@pytest.mark.timeout(300)
def test_extension_field_card_and_page_in_real_browser(tmp_path):
    pytest.importorskip("playwright.async_api")
    import uvicorn  # noqa: PLC0415 - optional test dependency
    from playwright.async_api import async_playwright  # noqa: PLC0415 - optional test dependency
    from tortoise import Model, Tortoise, fields  # noqa: PLC0415 - optional test dependency

    module = ModuleType("browser_extension_models")
    sys.modules["browser_extension_models"] = module

    class Product(Model):
        name = fields.CharField(max_length=120)
        rating = fields.IntField(default=0)

        class Meta:
            app = "browser_extension_models"
            table = "browser_extension_product"

    Product.__module__ = "browser_extension_models"
    module.Product = Product

    class ProductResource(Resource):
        model = Product
        fields: ClassVar[list[Field]] = [
            Text("name", required=True).searchable(),
            RatingField("rating", label="Rating", required=True),
        ]

    async def scenario():
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"browser_extension_models": ["browser_extension_models"]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas()
        for name, rating in (("Espresso", 5), ("Mug", 4), ("Kettle", 4), ("Filters", 3)):
            await Product.create(name=name, rating=rating)

        app = Flaxon("extension-browser")
        dashboard = AdminDashboard(
            app,
            config=AdminConfig(extensions=[RatingExtension()]),
            store=None,
            users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
            upload_dir=str(tmp_path / "uploads"),
        )
        dashboard.register(ProductResource)

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
                page = await browser.new_page(viewport={"width": 1400, "height": 1100})
                console_errors: list[str] = []
                external: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text) if message.type == "error" else None,
                )
                page.on("pageerror", lambda error: console_errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: (
                        external.append(request.url)
                        if not request.url.startswith(origin) and not request.url.startswith("data:")
                        else None
                    ),
                )

                await page.goto(f"{origin}/admin/login")
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "Admin123!")
                await page.click("button.login-submit")
                await page.wait_for_url("**/admin/", timeout=15000)

                # --- Card: Teloce component rendered from real aggregated data.
                card = page.locator(".fx-rating-summary").first
                await card.wait_for(timeout=10000)
                assert "4.0" in await card.inner_text()
                assert "4 rated records" in await card.inner_text()

                # --- Tool: contributed link appears on the dashboard.
                tool = page.locator('[data-extension-tool="Rating insights"]')
                assert await tool.count() == 1

                # --- Page: SSR content is present before/without the bundle.
                await tool.click()
                await page.wait_for_url("**/admin/ratings", timeout=10000)
                table = page.locator(".fx-ratings-table")
                await table.wait_for(timeout=10000)
                assert "Products" in await table.inner_text()
                assert "4.0" in await table.inner_text()

                # --- Field: the component replaces the fallback control and saves.
                await page.goto(f"{origin}/admin/product/add")
                await page.wait_for_selector(".fx-teloce-field fieldset", timeout=10000)
                assert await page.locator(".fx-teloce-field select").count() == 0
                assert await page.locator(".fx-teloce-field input[type=radio]").count() == 5

                await page.fill('input[name="name"]', "Cold brew")
                await page.locator(".fx-teloce-field label").nth(4).click()
                checked = page.locator(".fx-teloce-field input[type=radio]:checked")
                assert await checked.get_attribute("value") == "5"
                assert "5 / 5" in await page.locator(".fx-rating-value").inner_text()

                await page.screenshot(path=str(shot_dir / "admin-extensions.png"), full_page=True)

                await page.locator('form:has(input[name="name"]) button[type="submit"]').first.click()
                await page.wait_for_url("**/admin/product", timeout=15000)
                record = await Product.filter(name="Cold brew").first()
                assert record is not None and record.rating == 5

                rows = await page.locator("table tbody tr").all_text_contents()
                assert any("Cold brew" in row for row in rows), rows

                # --- No console errors, and nothing loaded from a CDN.
                assert console_errors == [], console_errors
                assert external == [], external
                await browser.close()
        finally:
            await Tortoise.close_connections()
            sys.modules.pop("browser_extension_models", None)
            server.should_exit = True
            await task

    asyncio.run(scenario())
