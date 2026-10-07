"""Jinax strict context behavior and boundary cases."""

import pytest
from jinja2 import UndefinedError

from flaxon.jinax import Jinax


@pytest.mark.asyncio
async def test_missing_required_context_raises(tmp_path):
    (tmp_path / "page.html").write_text("{{ missing }}")
    with pytest.raises(UndefinedError):
        await Jinax(tmp_path).render("page.html")


@pytest.mark.asyncio
async def test_relaxed_undefined_renders_empty_value(tmp_path):
    (tmp_path / "page.html").write_text("<p>{{ missing }}</p>")
    assert await Jinax(tmp_path, strict_undefined=False).render("page.html") == "<p></p>"


@pytest.mark.asyncio
async def test_registered_globals_and_filters_are_available(tmp_path):
    (tmp_path / "page.html").write_text("{{ greeting }} {{ name|reverse_name }}")
    engine = Jinax(tmp_path)
    engine.add_global("greeting", "Hello")
    engine.add_filter("reverse_name", lambda value: value[::-1])
    assert await engine.render("page.html", {"name": "Ada"}) == "Hello adA"
