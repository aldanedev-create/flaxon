"""Real-browser checks for SSR, runtime overlays and request correlation."""

import os
import socket
import threading
import time

import pytest

from flaxon import Flaxon, Request

pytestmark = pytest.mark.skipif(
    os.getenv("FLAXON_BROWSER_TESTS") != "1", reason="Enable Chromium browser tests"
)


@pytest.mark.parametrize("debug", [True, False])
def test_ssr_browser_errors_reach_dashboard(tmp_path, debug):
    import uvicorn
    from playwright.sync_api import sync_playwright

    (tmp_path / "ui").mkdir()
    (tmp_path / "ui/app.html").write_text("""<template>
      <main><h1>{{ title }}</h1><p>{{ count.value }}</p>
        <button @click="count.value++">Count</button>
        <button @click="fail">Fail</button>
        <a href="/projects" data-teloce-link>Projects</a>
        <div data-teloce-router-view></div>
      </main>
    </template>
    <script>export default {data(){return {title:'Default',count:signal(0)}},methods:{fail(){throw new Error('Browser example failed')}}}</script>
    <style scoped>main{padding:1rem}</style>""")
    (tmp_path / "ui/pages").mkdir()
    (tmp_path / "ui/pages/projects.html").write_text("<template><h2>Projects screen</h2></template>")
    app = Flaxon("Debugger browser", debug=debug)
    app.use_teloce(project_root=tmp_path, options={"ssr": "opt-in"})

    @app.get("/")
    async def home(request: Request):
        return await request.compile("app.html", {"title": "SSR title", "count": {"value": 4}}, ssr=True)

    @app.get("/api/fail")
    async def fail():
        raise RuntimeError("Backend example failed")

    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline, "Server failed to start"
            time.sleep(0.02)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            page.set_default_timeout(5000)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_function("window.__FLAXON_TELOCE__")
            assert page.locator("h1").inner_text() == "SSR title"
            assert page.locator("p").inner_text() == "4"
            page.get_by_role("button", name="Count", exact=True).click()
            page.wait_for_function('document.querySelector("p").textContent==="5"')
            page.evaluate("window.navigationSentinel = true")
            page.get_by_role("link", name="Projects", exact=True).click()
            page.wait_for_url(f"http://127.0.0.1:{port}/projects")
            page.get_by_role("heading", name="Projects screen").wait_for()
            assert page.evaluate("window.navigationSentinel === true")
            if not debug:
                assert app.teloce.build_result["bundle"]
                assert page.locator("dialog[data-flaxon-error]").count() == 0
                assert (
                    page.request.post(f"http://127.0.0.1:{port}/__debug__/teloce/errors", data={}).status
                    == 404
                )
                browser.close()
                return
            page.get_by_role("button", name="Fail", exact=True).click()
            page.locator("dialog[data-flaxon-error]").wait_for()
            page.wait_for_function(
                'document.querySelector("dialog pre").textContent.includes("ui/app.html:")'
            )
            assert any(item["message"] == "Browser example failed" for item in app.error_store.get_recent())
            page.get_by_role("button", name="Dismiss").click()
            page.evaluate('fetch("/api/fail")')
            page.wait_for_function(
                'document.querySelector("dialog pre").textContent.includes("/api/fail returned 500")'
            )
            deadline = time.monotonic() + 5
            while not any(item["type"] == "Teloce api" for item in app.error_store.get_recent()):
                assert time.monotonic() < deadline
                page.wait_for_timeout(50)
            report = next(item for item in app.error_store.get_recent() if item["type"] == "Teloce api")
            assert report["request_id"]
            related = app.error_store.get(report["related_error_id"])
            assert (
                related["request_id"] == report["request_id"] and "Backend example failed" in related["stack"]
            )
            page.goto(f"http://127.0.0.1:{port}/__debug__")
            assert "Browser example failed" in page.locator("body").inner_text()
            assert "Teloce api" in page.locator("body").inner_text()
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
