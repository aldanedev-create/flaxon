"""Real-browser checks for generated ORM forms and relationship controls."""

import os
import secrets
import socket
import subprocess
import sys
import time
import httpx
import pytest


@pytest.mark.timeout(90)
def test_orm_admin_forms(tmp_path):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    from tests.integration.test_admin_orm_experience import test_admin_orm_experience

    test_admin_orm_experience(tmp_path)
    root = tmp_path / "admin_experience"
    password = secrets.token_urlsafe(25) + "Aa1!"
    environment = dict(os.environ, FLAXON_BROWSER_TEST_PASSWORD=password)
    seed = """import os
from app import app
admin = app._flaxon_admin_dashboard
record = admin.auth.add_user({"username": "browser_operator", "password": os.environ["FLAXON_BROWSER_TEST_PASSWORD"], "permissions": ["admin.superuser"]})
admin.store.set("users", "browser_operator", record)
admin.store.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", seed], cwd=root, env=environment, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)],
        cwd=root,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(origin + "/admin/login", trust_env=False).status_code == 200:
                    break
            except httpx.ConnectError:
                pass
            time.sleep(0.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(timeout=10000)
            page = browser.new_page()
            page.route(
                "**/*",
                lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort(),
            )
            errors = []
            page.set_default_timeout(10000)
            page.set_default_navigation_timeout(10000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/admin/login", wait_until="domcontentloaded")
            page.locator('[name="username"]').fill("browser_operator")
            page.locator('[name="password"]').fill(password)
            page.locator('form button:not([type="button"])').first.click(no_wait_after=True)
            page.wait_for_url(origin + "/admin/", wait_until="domcontentloaded")
            page.goto(origin + "/admin/project/add", wait_until="domcontentloaded")
            page.locator('[name="name"]').fill("Browser parent")
            page.locator("[data-inline-add]").click()
            page.locator('[data-child-field="title"]').fill("Browser child")
            page.locator('form button:not([type="button"])').first.click(no_wait_after=True)
            page.wait_for_url(origin + "/admin/project", wait_until="domcontentloaded")
            page.goto(origin + "/admin/task/add", wait_until="domcontentloaded")
            page.locator('[name="title"]').fill("Browser task")
            page.locator("[data-related-search]").fill("Browser parent")
            page.wait_for_function("document.querySelector('[data-related-results]').options.length > 1")
            page.locator("[data-related-results]").select_option(index=1)
            page.locator('form button:not([type="button"])').first.click(no_wait_after=True)
            page.wait_for_url(origin + "/admin/task", wait_until="domcontentloaded")
            assert "Browser task" in page.content()
            # More than 100 related records also gives many-to-many search.
            page.goto(origin + "/admin/team/add", wait_until="domcontentloaded")
            page.locator('[name="name"]').fill("Browser team")
            page.locator("[data-related-search]").fill("Browser parent")
            page.wait_for_function("document.querySelector('[data-related-results]').options.length > 0")
            page.locator("[data-related-results]").select_option(index=0)
            page.locator('form button:not([type="button"])').first.click(no_wait_after=True)
            page.wait_for_url(origin + "/admin/team", wait_until="domcontentloaded")
            assert "Browser team" in page.content()
            assert not errors, errors
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(origin + "/admin/task/add", wait_until="domcontentloaded")
            assert page.locator("[data-related-search]").is_visible()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
