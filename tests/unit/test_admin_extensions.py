"""Unit contract for Teloce-backed admin extensions."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from flaxon.admin import extensions as extension_module
from flaxon.admin.extensions import (
    AdminExtension,
    Component,
    ExtensionError,
    ExtensionPage,
    ExtensionRegistry,
    TeloceField,
    load_extensions,
)
from flaxon.admin.resources import Field


class StubDistribution:
    def __init__(self, name: str) -> None:
        self.name = name


class StubEntryPoint:
    def __init__(self, name: str, distribution: str, target: object) -> None:
        self.name = name
        self.value = f"{name}=stub"
        self.dist = StubDistribution(distribution)
        self._target = target

    def load(self) -> object:
        return self._target


class StubExtension(AdminExtension):
    name = "stub"
    label = "Stub"


def test_component_rejects_unsafe_names():
    with pytest.raises(ValueError):
        Component("../escape", "<template><p>x</p></template>")


def test_component_reports_compile_errors(monkeypatch):
    def broken_compile(source, filename):
        return {"success": False, "diagnostics": {"errors": [{"message": "unexpected token"}]}}

    monkeypatch.setattr(extension_module, "_teloce_module", lambda: SimpleNamespace(compile=broken_compile))
    component = Component("broken", "<template><p>x</p></template>")
    with pytest.raises(ExtensionError, match="unexpected token"):
        component.compile()


def test_mount_point_escapes_props_and_value():
    component = Component("rating", "<template><p>x</p></template>")
    html = component.mount_point(
        {"label": "</div><script>alert(1)</script>"},
        value='"><img src=x onerror=alert(1)>',
        body="<p>fallback</p>",
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;/div&gt;" in html
    assert "<img" not in html
    assert html.endswith("<p>fallback</p></div>")


def test_load_extensions_ignores_foreign_distributions(caplog):
    entry_points = [
        StubEntryPoint("sneaky", "unrelated-package", StubExtension),
        StubEntryPoint("stub", "flaxon-admin-stub", StubExtension),
    ]
    loaded = load_extensions(entry_points=entry_points)
    assert [item.name for item in loaded] == ["stub"]
    assert "must come from a flaxon-admin-* distribution" in caplog.text


def test_load_extensions_honours_disabled_names():
    entry_points = [StubEntryPoint("stub", "flaxon-admin-stub", StubExtension)]
    assert load_extensions(entry_points=entry_points, disabled=("flaxon-admin-stub",)) == []
    assert load_extensions(entry_points=entry_points, disabled=("stub",)) == []


def test_load_extensions_rejects_non_extensions():
    entry_points = [StubEntryPoint("bad", "flaxon-admin-bad", object)]
    with pytest.raises(TypeError, match="did not resolve to an AdminExtension"):
        load_extensions(entry_points=entry_points)


def test_registry_load_deduplicates_discovered_and_included_extensions(monkeypatch):
    """An explicit include of an already-discovered extension must be a no-op."""
    found = StubExtension()

    monkeypatch.setattr(extension_module, "load_extensions", lambda **kwargs: [found])
    dashboard = SimpleNamespace(
        config=SimpleNamespace(disabled_extensions=()), register_metric=lambda card: card
    )
    registry = ExtensionRegistry(dashboard)
    # The same logical extension arrives both from discovery and from include.
    registry.load(include=[StubExtension()])
    assert [extension.name for extension in registry.extensions] == ["stub"]


def test_registry_rejects_duplicate_extension_names():
    dashboard = SimpleNamespace(
        config=SimpleNamespace(disabled_extensions=()), register_metric=lambda card: card
    )
    registry = ExtensionRegistry(dashboard)
    registry.register(StubExtension())
    with pytest.raises(ExtensionError, match="already registered"):
        registry.register(StubExtension())


def test_registry_rejects_two_components_with_the_same_name(tmp_path: Path):
    first = tmp_path / "a" / "ui"
    second = tmp_path / "b" / "ui"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "widget.vel").write_text("<template><p>a</p></template>", encoding="utf-8")
    (second / "widget.vel").write_text("<template><p>b</p></template>", encoding="utf-8")

    class First(AdminExtension):
        name = "first"

        def __init__(self) -> None:
            super().__init__(root=first.parent)

    class Second(AdminExtension):
        name = "second"

        def __init__(self) -> None:
            super().__init__(root=second.parent)

    dashboard = SimpleNamespace(
        config=SimpleNamespace(disabled_extensions=()), register_metric=lambda card: card
    )
    registry = ExtensionRegistry(dashboard)
    registry.register(First())
    with pytest.raises(ExtensionError, match="contributed twice"):
        registry.register(Second())


def test_component_cannot_escape_the_extension_root(tmp_path: Path):
    extension = StubExtension(root=tmp_path)
    with pytest.raises(ExtensionError, match="inside the ui directory"):
        extension.component("../secret.vel")


def test_teloce_field_exposes_component_and_fallback():
    component = Component("rating", "<template><p>x</p></template>")
    field = TeloceField(
        "score",
        component,
        label="Score",
        required=True,
        fallback="select",
        fallback_choices=[(value, f"{value} stars") for value in range(1, 6)],
        props={"max": 5},
    )
    entry = field.schema_entry()
    assert entry["kind"] == "teloce"
    assert entry["widget"] == "admin/extensions/field.html"
    assert entry["component"] == "rating"
    assert entry["fallback"] == "select"
    assert entry["fallback_choices"][0] == ["1", "1 stars"]
    assert json.loads(entry["component_props"]) == {
        "name": "score",
        "label": "Score",
        "required": True,
        "max": 5,
    }


def test_teloce_field_rejects_unknown_fallback():
    with pytest.raises(ValueError, match="fallback"):
        TeloceField("score", Component("rating", "<template><p>x</p></template>"), fallback="richtext")


def test_teloce_field_is_a_normal_validated_field():
    field = TeloceField("score", Component("rating", "<template><p>x</p></template>"))
    assert isinstance(field, Field)
    assert field.clean("4") == "4"


def test_extension_page_defaults_to_dashboard_permission():
    page = ExtensionPage("ratings", Component("ratings", "<template><p>x</p></template>"))
    assert page.permission == "admin.view_dashboard"
    assert page.url == "ratings"
