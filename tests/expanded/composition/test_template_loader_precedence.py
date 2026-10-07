"""Template loader precedence behavior and boundary cases."""

import pytest

from flaxon.jinax import Jinax
from flaxon.jinax.loaders.composite import CompositeLoader
from flaxon.jinax.loaders.dictionary import DictionaryLoader
from flaxon.modules import FlaxonModule


def test_first_loader_wins_and_fallback_supplies_missing_template():
    first = DictionaryLoader({"shared.html": "first"})
    second = DictionaryLoader({"shared.html": "second", "only.html": "fallback"})
    loader = CompositeLoader([first, second])
    assert loader.get_source(None, "shared.html")[0] == "first"
    assert loader.get_source(None, "only.html")[0] == "fallback"
    assert set(loader.list_templates()) == {"shared.html", "only.html"}


def test_missing_template_raises_after_all_loaders():
    with pytest.raises(FileNotFoundError):
        CompositeLoader([DictionaryLoader()]).get_source(None, "missing.html")


@pytest.mark.asyncio
async def test_app_templates_win_and_module_templates_remain_available(app, tmp_path):
    primary = tmp_path / "app"
    secondary = tmp_path / "module"
    primary.mkdir()
    secondary.mkdir()
    (primary / "shared.html").write_text("app")
    (secondary / "shared.html").write_text("module")
    (secondary / "only.html").write_text("fallback")
    app.use_templates(Jinax(primary))
    app.mount_module(FlaxonModule("templates", template_dir=str(secondary)))
    assert await app.jinax.render("shared.html") == "app"
    assert await app.jinax.render("only.html") == "fallback"
