"""Keyboard-only create/edit for a declarative Resource admin (real browser)."""

from __future__ import annotations

import asyncio
from typing import ClassVar

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.resources import Email, Field, Resource, Text


class KeyboardOrder:
    rows: ClassVar[dict[str, dict]] = {}

    def __init__(self, **values):
        self.__dict__.update(values)
        self.pk = values.get("id", "")

    @classmethod
    def get_instances(cls):
        return [cls(**row) for row in cls.rows.values()]

    @classmethod
    def get_instance(cls, object_id):
        row = cls.rows.get(str(object_id))
        return cls(**row) if row else None

    @classmethod
    def create_instance(cls, data):
        identifier = str(len(cls.rows) + 1)
        cls.rows[identifier] = {"id": identifier, **data}
        return cls(**cls.rows[identifier])

    @classmethod
    def update_instance(cls, object_id, data):
        cls.rows[str(object_id)].update(data)
        return cls.get_instance(object_id)


@pytest.mark.timeout(120)
def test_keyboard_only_create_and_edit(tmp_path):  # noqa: C901 - browser scenario
    pytest.importorskip("playwright.async_api")
    import uvicorn  # noqa: PLC0415 - optional test dependency
    from playwright.async_api import async_playwright  # noqa: PLC0415 - optional test dependency

    KeyboardOrder.rows = {}
    app = Flaxon("keyboard-resource")
    dashboard = AdminDashboard(
        app,
        users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]}],
        upload_dir=str(tmp_path / "uploads"),
    )

    class OrderResource(Resource):
        model = KeyboardOrder
        fields: ClassVar[list[Field]] = [
            Text("reference", required=True).show_on_index(),
            Email("contact").help("Used for order notices"),
        ]

    dashboard.register(OrderResource)

    async def scenario():
        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())
        for _ in range(100):
            if server.started:
                break
            await asyncio.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                page = await browser.new_page()
                # No mouse clicks anywhere in this scenario.
                await page.goto(f"{origin}/admin/login")

                async def tab_until(script: str, limit: int = 10) -> None:
                    for _ in range(limit):
                        if await page.evaluate(script):
                            return
                        await page.keyboard.press("Tab")
                    raise AssertionError(f"Keyboard focus never reached {script}")

                await tab_until("() => document.activeElement?.name === 'username'")
                await page.keyboard.type("admin")
                await page.keyboard.press("Tab")
                await page.keyboard.type("Admin123!")
                await tab_until(
                    "() => document.activeElement?.tagName === 'BUTTON' "
                    "&& document.activeElement.type === 'submit'"
                )
                await page.keyboard.press("Enter")
                await page.wait_for_url("**/admin/", timeout=15000)

                await page.goto(f"{origin}/admin/order/add")
                await page.locator("#field-reference").focus()
                await page.keyboard.type("KB-1")
                await page.keyboard.press("Tab")
                await page.keyboard.type("buyer@example.com")
                # Submit using the keyboard only: focus the submit button via Tab chain.
                for _ in range(12):
                    focused = await page.evaluate("() => document.activeElement?.outerHTML || ''")
                    if 'type="submit"' in focused:
                        break
                    await page.keyboard.press("Tab")
                await page.keyboard.press("Enter")
                await page.wait_for_url("**/admin/order", timeout=15000)

                await page.goto(f"{origin}/admin/order/1/edit")
                await page.locator("#field-reference").focus()
                await page.keyboard.press("End")
                await page.keyboard.type("-EDITED")
                for _ in range(12):
                    focused = await page.evaluate("() => document.activeElement?.outerHTML || ''")
                    if 'value="list"' in focused:
                        break
                    await page.keyboard.press("Tab")
                await page.keyboard.press("Enter")
                await page.wait_for_url("**/admin/order", timeout=15000)

                assert KeyboardOrder.rows["1"]["reference"] == "KB-1-EDITED"
                await browser.close()
        finally:
            server.should_exit = True
            await task

    asyncio.run(scenario())
