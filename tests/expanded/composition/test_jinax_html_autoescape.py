"""Jinax html autoescape behavior and boundary cases."""

import pytest

from flaxon.jinax import Jinax


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["html", "htm", "xml"])
async def test_untrusted_markup_is_escaped(tmp_path, suffix):
    name = "page." + suffix
    (tmp_path / name).write_text("<p>{{ value }}</p>")
    html = await Jinax(tmp_path).render(name, {"value": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.asyncio
async def test_html_response_keeps_status_headers_and_utf8(tmp_path):
    (tmp_path / "page.html").write_text("<p>{{ name }}</p>")
    response = await Jinax(tmp_path).render_response(
        "page.html", {"name": "Zoë"}, status_code=201, headers={"X-Page": "created"}
    )
    assert response.status_code == 201
    assert response.body.decode() == "<p>Zoë</p>"
    assert response.headers["x-page"] == "created"
