"""Phase 3 acceptance: class-based actions run end-to-end in a real browser.

Boots the real ASGI app under uvicorn against a seeded Tortoise/SQLite database,
logs in, drives the bulk-action form in Chromium, and verifies the action had a
real, persisted side effect. A screenshot of the running app is captured (written
to a docs directory when FLAXON_DOCS_SCREENSHOT_DIR is set).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

from flaxon import Flaxon
from flaxon.admin import Action, ActionResult, AdminDashboard


@pytest.mark.timeout(180)
def test_approve_orders_action_runs_in_real_browser(tmp_path):
    pytest.importorskip("playwright.async_api")
    import uvicorn  # noqa: PLC0415 - optional test dependency
    from playwright.async_api import async_playwright  # noqa: PLC0415 - optional test dependency
    from tortoise import Model, Tortoise, fields  # noqa: PLC0415 - optional test dependency

    module = ModuleType("browser_action_models")
    sys.modules["browser_action_models"] = module

    class Order(Model):
        reference = fields.CharField(max_length=50)
        status = fields.CharField(max_length=20)

        class Meta:
            app = "browser_action_models"
            table = "browser_action_order"

    Order.__module__ = "browser_action_models"
    module.Order = Order

    class ApproveSelected(Action):
        name = "approve_selected"
        label = "Approve selected"
        confirmation = "Approve the selected orders?"

        async def handle(self, ids, params, context):
            model = context.admin_model.model
            approved, errors = [], []
            for object_id in ids:
                try:
                    await model.update_instance(object_id, {"status": "approved"})
                    approved.append(object_id)
                except Exception as exc:
                    errors.append({"id": object_id, "error": str(exc)})
            return ActionResult.ok(f"Approved {len(approved)} order(s).", errors=errors)

    async def scenario():
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"browser_action_models": ["browser_action_models"]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas()
        for index in range(4):
            await Order.create(reference=f"ORD-{index}", status="pending")

        app = Flaxon("actions-browser")
        dashboard = AdminDashboard(
            app,
            users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
            upload_dir=str(tmp_path / "uploads"),
            storage_path=str(tmp_path / "admin.sqlite3"),
        )
        dashboard.register(Order, list_display=["reference", "status"], fields=["reference", "status"])
        dashboard.register_action(ApproveSelected(), model=Order)

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
                page = await browser.new_page(viewport={"width": 1280, "height": 900})
                await page.goto(f"{origin}/admin/login")
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "Admin123!")
                await page.click("button.login-submit")
                await page.wait_for_url("**/admin/", timeout=15000)

                # The action is offered in the model's bulk-action selector.
                await page.goto(f"{origin}/admin/order")
                options = await page.locator('#bulk-form select[name="action"] option').all_text_contents()
                assert "Approve selected" in options, options

                # Drive the real bulk-action form: select two rows and run the action.
                dialog_accepted = []
                dialog_tasks = []

                def accept_dialog(dialog):
                    dialog_accepted.append(dialog.message)
                    dialog_tasks.append(asyncio.create_task(dialog.accept()))

                page.on("dialog", accept_dialog)
                boxes = page.locator('input[name="ids"][form="bulk-form"]')
                assert await boxes.count() == 4
                await boxes.nth(0).check()
                await boxes.nth(1).check()
                await page.select_option('#bulk-form select[name="action"]', "approve_selected")
                await page.click("#bulk-form button")
                await page.wait_for_url("**/admin/order", timeout=15000)
                await asyncio.sleep(0.3)

                # Verify the persisted side effect in the real database.
                statuses = {row.reference: row.status for row in await Order.all()}
                assert statuses["ORD-0"] == "approved"
                assert statuses["ORD-1"] == "approved"
                assert statuses["ORD-2"] == "pending" and statuses["ORD-3"] == "pending"

                # The confirmation text was actually shown to the operator.
                assert dialog_accepted and "Approve the selected orders?" in dialog_accepted[0]

                # Full audit entry exists for this action run.
                entries = dashboard.store.get("audit", "entries", []) or []
                assert any(
                    e["details"].get("details", {}).get("action") == "approve_selected" for e in entries
                )

                shot_dir = os.environ.get("FLAXON_DOCS_SCREENSHOT_DIR")
                target = (Path(shot_dir) if shot_dir else tmp_path) / "admin-actions.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(target), full_page=True)
                assert target.exists() and target.stat().st_size > 1000
                await browser.close()
        finally:
            await Tortoise.close_connections()
            sys.modules.pop("browser_action_models", None)
            server.should_exit = True
            await task

    asyncio.run(scenario())
