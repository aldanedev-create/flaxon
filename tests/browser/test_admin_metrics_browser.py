"""Phase 2 acceptance: all five metrics render from real seeded data.

Boots the real ASGI app under uvicorn, seeds a real Tortoise/SQLite database,
and verifies in Chromium that Value/Trend/Partition/Progress/Table render as
inline, offline, accessible SVG. A screenshot is captured from the running app
(and written to a docs directory when FLAXON_DOCS_SCREENSHOT_DIR is set).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.metrics import Partition, Progress, Table, Trend, Value


@pytest.mark.timeout(180)
def test_all_five_metrics_render_in_real_browser(tmp_path):
    pytest.importorskip("playwright.async_api")
    import uvicorn  # noqa: PLC0415 - optional test dependency
    from playwright.async_api import async_playwright  # noqa: PLC0415 - optional test dependency
    from tortoise import Model, Tortoise, fields  # noqa: PLC0415 - optional test dependency

    module = ModuleType("browser_metrics_models")
    sys.modules["browser_metrics_models"] = module

    class Order(Model):
        reference = fields.CharField(max_length=50)
        amount = fields.DecimalField(max_digits=10, decimal_places=2)
        status = fields.CharField(max_length=20)
        fulfilled = fields.BooleanField(default=False)
        created_at = fields.DatetimeField()

        class Meta:
            app = "browser_metrics_models"
            table = "browser_metrics_order"

    Order.__module__ = "browser_metrics_models"
    module.Order = Order

    async def scenario():
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"browser_metrics_models": ["browser_metrics_models"]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas()
        # Seed relative to real "now": the dashboard resolves ranges against
        # the current clock, so fixed historical dates would fall outside 30d.
        now = datetime.now(UTC)
        for index in range(10):
            await Order.create(
                reference=f"ORD-{index}",
                amount=index + 1,
                status="paid" if index % 2 == 0 else "pending",
                fulfilled=index % 3 == 0,
                created_at=now - timedelta(days=index % 3),
            )

        app = Flaxon("metrics-browser")
        dashboard = AdminDashboard(
            app,
            users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
            upload_dir=str(tmp_path / "uploads"),
        )
        # Register the model so the dashboard can count it, then all five cards.
        dashboard.register(Order, list_display=["reference", "amount", "status"])
        common = {"model": Order, "range": "30d", "date_field": "created_at"}
        dashboard.register_metric(Value(title="Total orders", **common))
        dashboard.register_metric(Trend(title="Orders per day", **common))
        dashboard.register_metric(Partition(title="Orders by status", field="status", **common))
        dashboard.register_metric(Progress(title="Fulfilled", current_filter={"fulfilled": True}, **common))
        dashboard.register_metric(
            Table(title="Top orders", columns=["reference", "amount"], limit=3, **common)
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
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1280, "height": 1400})
                await page.goto(f"{origin}/admin/login")
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "Admin123!")
                await page.click("button.login-submit")
                await page.wait_for_url("**/admin/", timeout=15000)

                cards = page.locator(".fx-metric-card")
                count = await cards.count()
                assert count == 5, f"expected five metric cards, got {count}"

                titles = await page.locator(".fx-metric-title").all_text_contents()
                for expected in (
                    "Total orders",
                    "Orders per day",
                    "Orders by status",
                    "Fulfilled",
                    "Top orders",
                ):
                    assert expected in titles, titles

                # All five are inline SVG with an accessible text alternative.
                svgs = await page.locator(".fx-metric-card svg").count()
                assert svgs == 5
                roles = await page.locator(".fx-metric-card svg[role='img']").count()
                assert roles == 5
                desc = await page.locator(".fx-metric-card svg desc").count()
                assert desc == 5

                # Offline: metric cards contain no scripts and no remote URLs.
                markup = await page.locator(".fx-metrics-panel").inner_html()
                assert "<script" not in markup
                assert "http://" not in markup and "https://" not in markup
                # Data came from the seeded DB, not placeholders. Each SVG
                # encodes its computed value from real SQL aggregation.
                value_svg = await cards.nth(0).locator("svg").inner_html()
                assert ">10<" in value_svg, value_svg  # Total orders = 10 seeded rows
                fulfilled_svg = await cards.nth(3).locator("svg").inner_html()
                assert "/ 10" in fulfilled_svg, fulfilled_svg  # Progress target = 10
                assert "40%" in fulfilled_svg, fulfilled_svg  # 4 of 10 fulfilled (index % 3 == 0)
                table_svg = await cards.nth(4).locator("svg").inner_html()
                assert "ORD-0" in table_svg and "ORD-2" in table_svg, table_svg  # real seeded rows

                shot_dir = os.environ.get("FLAXON_DOCS_SCREENSHOT_DIR")
                if shot_dir:
                    target = Path(shot_dir) / "admin-metrics.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(target), full_page=True)
                else:
                    target = tmp_path / "admin-metrics.png"
                    await page.screenshot(path=str(target), full_page=True)
                assert target.exists() and target.stat().st_size > 1000
                await browser.close()
        finally:
            await Tortoise.close_connections()
            sys.modules.pop("browser_metrics_models", None)
            server.should_exit = True
            await task

    asyncio.run(scenario())
