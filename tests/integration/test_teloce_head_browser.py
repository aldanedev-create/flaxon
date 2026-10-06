"""Opt-in real-browser check for the TypeScript/CDN teaching application."""
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import threading
import time

import pytest


@pytest.mark.skipif(os.getenv("FLAXON_BROWSER_TESTS") != "1", reason="Set FLAXON_BROWSER_TESTS=1 and install Playwright Chromium")
def test_typescript_converter_and_cdn_collapse(tmp_path):
    import uvicorn
    from playwright.sync_api import sync_playwright

    source = Path(__file__).resolve().parents[2] / "examples/teloce_head_ts"
    shutil.copytree(source, tmp_path / "example")
    spec = importlib.util.spec_from_file_location("browser_head_example", tmp_path / "example/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(module.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Example server did not start")
            time.sleep(.05)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/")
            page.get_by_text("Python serves the API; Teloce runs the interface.").wait_for()
            page.locator("#miles").fill("2")
            page.get_by_role("button", name="Convert", exact=True).click()
            page.get_by_role("status").filter(has_text="3.219 km").wait_for()
            page.wait_for_function("typeof window.bootstrap !== 'undefined'")
            page.get_by_role("button", name="How it works", exact=True).click()
            page.locator("#details.show").wait_for()
            assert page.title() == "Pocket Converter"
            assert page.locator('html').get_attribute('lang') == 'en'
            assert page.locator('link[rel="icon"]').get_attribute('href') == '/static/favicon.svg'
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.mark.skipif(os.getenv("FLAXON_BROWSER_TESTS") != "1", reason="Set FLAXON_BROWSER_TESTS=1 and install Playwright Chromium")
def test_typed_html_taskboard_creates_a_task(tmp_path):
    import uvicorn
    from playwright.sync_api import sync_playwright

    source = Path(__file__).resolve().parents[2] / "examples/teloce_taskboard"
    shutil.copytree(source, tmp_path / "example")
    spec = importlib.util.spec_from_file_location("browser_taskboard_example", tmp_path / "example/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(module.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Example server did not start")
            time.sleep(.05)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/")
            page.get_by_role("heading", name="Read the full-stack lessons").wait_for()
            page.locator("#task-title").fill("Write readable lessons")
            page.get_by_role("button", name="Add task", exact=True).click()
            page.get_by_role("heading", name="Write readable lessons").wait_for()
            page.get_by_role("button", name="Refresh tasks", exact=True).click()
            page.get_by_role("heading", name="Write readable lessons").wait_for()
            assert page.title() == "Taskboard"
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
