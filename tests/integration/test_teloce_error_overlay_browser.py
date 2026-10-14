"""The browser error overlay is interactive, readable and isolated from the app it debugs."""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("FLAXON_BROWSER_TESTS") != "1", reason="Enable Chromium browser tests"
)

ORIGIN = "http://localhost:9"
CLIENT = Path(__file__).parents[2] / "src/flaxon/debugging/teloce-client.js"
PAGE = """<!doctype html><meta charset="utf-8"><title>App</title>
<style>%(css)s</style><h1>App</h1>
<script type="module">
import { installTeloceDebugger } from '/client.js';
window.__reply = { error_id: 'fx_1' }; window.__delay = 0;
window.fetch = async () => {
  await new Promise(resolve => setTimeout(resolve, window.__delay));
  return { ok: true, status: 200, json: async () => window.__reply };
};
installTeloceDebugger({ token: 't', revision: 'r' });
window.__fire = detail => window.dispatchEvent(new CustomEvent('teloce:error', { detail }));
window.__ready = true;
</script>"""

STACK = "\n".join(
    ["TypeError: boom"] + [f"    at fn{i} ({ORIGIN}/_flaxon/app.js:{i}:1)" for i in range(1, 8)]
)
REPORT = {
    "category": "runtime",
    "message": "Uncaught TypeError: boom",
    "filename": f"{ORIGIN}/_flaxon/app.js",
    "line": 4,
    "column": 17,
    "stack": STACK,
}
SERVER_CONTEXT = {
    "error_id": "fx_2",
    "location": "ui/app.html:4:17",
    "source_excerpt": "3: <script>\n4:   const label = user.name;\n5: </script>",
}


@pytest.fixture
def open_overlay_page():
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 - optional dependency

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])

        def open_page(css="", reply=None, delay=0):
            context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
            page = context.new_page()
            page.set_default_timeout(5000)

            def serve(route):
                script = route.request.url.endswith("/client.js")
                route.fulfill(
                    body=CLIENT.read_text() if script else PAGE % {"css": css},
                    content_type="text/javascript" if script else "text/html",
                )

            page.route(f"{ORIGIN}/**", serve)
            page.goto(f"{ORIGIN}/")
            page.wait_for_function("window.__ready")
            page.evaluate(
                "([reply, delay]) => { window.__reply = reply; window.__delay = delay; }",
                [reply or {}, delay],
            )
            return page

        yield open_page
        browser.close()


def fire(page, report=None):
    page.evaluate("report => window.__fire(report)", report or REPORT)
    page.locator("dialog[data-flaxon-error][open]").wait_for()


def test_overlay_leads_with_the_message_and_shortens_the_path(open_overlay_page):
    page = open_overlay_page()
    fire(page)
    assert page.locator(".fx-title").inner_text() == "TypeError: boom"
    assert page.locator(".fx-kind").inner_text() == "Runtime error"
    assert page.locator(".fx-path").inner_text() == "/_flaxon/app.js:4:17"
    assert page.locator(".fx-frame").first.inner_text().startswith("fn1")


def test_clicking_the_path_copies_the_full_url_and_confirms(open_overlay_page):
    page = open_overlay_page()
    fire(page)
    page.locator(".fx-where").click()
    page.locator(".fx-hint", has_text="Copied").wait_for()
    assert page.evaluate("navigator.clipboard.readText()") == f"{ORIGIN}/_flaxon/app.js:4:17"
    page.get_by_role("button", name="Copy error").click()
    page.get_by_role("button", name="Copied").wait_for()
    assert "Uncaught TypeError: boom" in page.evaluate("navigator.clipboard.readText()")


def test_server_context_updates_in_place_and_extra_frames_expand(open_overlay_page):
    page = open_overlay_page(reply=SERVER_CONTEXT)
    fire(page)
    page.locator(".fx-hit").wait_for()
    assert page.locator(".fx-hit .fx-num").inner_text() == "4"
    assert page.locator(".fx-path").inner_text() == "ui/app.html:4:17"
    assert page.locator("dialog[data-flaxon-error]").count() == 1
    assert page.locator(".fx-frame:visible").count() == 6  # 5 frames and the "Show more" row
    page.get_by_role("button", name="Show 2 more").click()
    assert page.locator(".fx-frame:visible").count() == 7
    assert page.get_by_role("button", name="Show 2 more").count() == 0


def test_escape_dismisses_and_the_late_server_reply_does_not_reopen_it(open_overlay_page):
    page = open_overlay_page(reply=SERVER_CONTEXT, delay=300)
    fire(page)
    page.keyboard.press("Escape")
    page.wait_for_timeout(700)
    assert page.locator("dialog[data-flaxon-error][open]").count() == 0
    page.evaluate("window.__delay = 0")
    page.wait_for_timeout(2100)  # outside the 2s duplicate window
    fire(page)  # a fresh occurrence of the same error is shown again
    assert page.locator(".fx-title").inner_text() == "TypeError: boom"


def test_click_outside_closes_but_a_selection_drag_ending_outside_does_not(open_overlay_page):
    page = open_overlay_page()
    fire(page)
    title = page.locator(".fx-title").bounding_box()
    page.mouse.move(title["x"] + 20, title["y"] + 10)
    page.mouse.down()
    page.mouse.move(5, 5)
    page.mouse.up()
    assert page.locator("dialog[data-flaxon-error][open]").count() == 1
    page.mouse.click(5, 5)
    assert page.locator("dialog[data-flaxon-error][open]").count() == 0


def test_error_text_is_never_rendered_as_html(open_overlay_page):
    page = open_overlay_page()
    payload = '<img src=x onerror="window.__xss=1"><b>bold</b>'
    fire(page, {**REPORT, "message": payload, "stack": payload})
    page.wait_for_timeout(200)
    assert page.evaluate("window.__xss") is None
    assert page.locator("dialog img, dialog b").count() == 0
    assert payload in page.locator(".fx-title").inner_text()


def test_app_styles_cannot_restyle_the_overlay(open_overlay_page):
    """Ordinary global rules (resets, `button {}`, `h2 {}`) lose to the overlay's scoped selectors.

    Only `!important` on a global rule can still win; isolating against that needs Shadow DOM.
    """

    css = "h2{font-size:80px;color:red} button,a{background:red;color:red;border:9px solid red}"
    page = open_overlay_page(css=css)
    fire(page)
    assert page.eval_on_selector(".fx-title", "e => getComputedStyle(e).fontSize") == "18px"
    assert page.eval_on_selector(".fx-title", "e => getComputedStyle(e).color") == "rgb(230, 237, 240)"
    assert (
        page.eval_on_selector(".fx-btn:not(.fx-primary)", "e => getComputedStyle(e).backgroundColor")
        == "rgb(22, 27, 34)"
    )


def test_overlay_uses_the_dark_palette_and_keeps_focus_off_the_buttons(open_overlay_page):
    page = open_overlay_page()
    fire(page)
    styles = page.eval_on_selector("dialog", "e => getComputedStyle(e).backgroundColor")
    assert styles == "rgb(13, 17, 23)"
    assert page.evaluate("document.activeElement.tagName") == "DIALOG"
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement.getAttribute('aria-label')")
    assert focused == "Close"