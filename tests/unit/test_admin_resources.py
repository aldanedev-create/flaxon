"""Phase 1 contract: declarative Resource/Field admin API.

Every assertion here is written before the implementation exists. The module
import at the top is expected to fail until Phase 1 is implemented.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from flaxon.admin.resources import (
    BADGE,
    BOOLEAN,
    JSON as JSONField,  # noqa: N811 - public alias
    NUMBER,
    SELECT,
    TEXT,
    TEXTAREA,
    URL as URLField,  # noqa: N811 - public alias
    Badge,
    BelongsTo,
    Boolean,
    Code,
    Color,
    Currency,
    Date,
    DateTime,
    Email,
    Field,
    File,
    HasMany,
    Image,
    KeyValue,
    ManyToMany,
    Markdown,
    Number,
    Password,
    Resource,
    Select,
    Slug,
    Tags,
    Text,
    Textarea,
    augment_schema,
)
from flaxon.validation import FieldError, custom_validator, url_validator

ALL_FIELD_TYPES = [
    Text,
    Textarea,
    Number,
    Boolean,
    Select,
    Badge,
    Date,
    DateTime,
    Email,
    URLField,
    Password,
    Image,
    File,
    Markdown,
    Code,
    JSONField,
    KeyValue,
    Tags,
    Slug,
    Color,
    Currency,
    BelongsTo,
    HasMany,
    ManyToMany,
]


# --- fluent API --------------------------------------------------------------


def test_fluent_options_are_additive_and_chainable():
    field = Text("title")
    assert field.sortable() is field
    assert field.searchable() is field
    assert field.filterable() is field
    assert field.help("Shown on the list") is field
    assert field.show_on_index() is field
    assert field.show_on_detail(False) is field
    assert field.show_on_form() is field
    assert field.depends_on("kind", "digital") is field

    assert field.is_sortable is True
    assert field.is_searchable is True
    assert field.is_filterable is True
    assert field.help_text == "Shown on the list"
    assert field.on_index is True
    assert field.on_detail is False
    assert field.on_form is True
    assert field.depends == ("kind", "digital")

    assert field.readonly().is_readonly is True
    assert field.readonly(False).is_readonly is False


def test_rules_accept_framework_validators():
    def reject_bad(value, field):
        if value == "bad":
            raise FieldError("No bad values")

    field = Text("code").rules(custom_validator(reject_bad))
    assert len(field.validators) == 1
    with pytest.raises(FieldError):
        field.clean("bad")


def test_every_field_type_exposes_a_kind_and_a_validation_field():
    for cls in ALL_FIELD_TYPES:
        field = cls("value")
        assert isinstance(field, Field), cls.__name__
        assert isinstance(field.kind, str) and field.kind, cls.__name__
        assert field.validation_field() is not None, cls.__name__


def test_widget_kinds_match_the_semantics_of_each_type():
    # String constants are exported so plugins can declare kinds without importing classes.
    assert (TEXT, TEXTAREA, NUMBER, BOOLEAN, SELECT, BADGE) == (
        "text",
        "textarea",
        "number",
        "checkbox",
        "select",
        "badge",
    )
    assert Text("a").kind == "text"
    assert Textarea("a").kind == "textarea"
    assert Number("a").kind == "number"
    assert Boolean("a").kind == "checkbox"
    assert Select("a", choices=[("x", "X")]).kind == "select"
    assert Badge("a", choices=[("x", "X")]).kind == "badge"
    assert Date("a").kind == "date"
    assert DateTime("a").kind == "datetime-local"
    assert Email("a").kind == "email"
    assert URLField("a").kind == "url"
    assert Password("a").kind == "password"
    assert Image("a").kind == "image"
    assert File("a").kind == "file"
    assert Markdown("a").kind == "textarea"
    assert Code("a").kind == "textarea"
    assert JSONField("a").kind == "textarea"
    assert KeyValue("a").kind == "textarea"
    assert Tags("a").kind == "textarea"
    assert Slug("a").kind == "text"
    assert Color("a").kind == "color"
    assert Currency("a").kind == "number"
    assert BelongsTo("a").kind == "select"
    assert HasMany("a").kind == "many"
    assert ManyToMany("a").kind == "many"


# --- server-side validation uses the API's rules -----------------------------


def test_required_validation_uses_flaxon_field_error():
    field = Text("name", required=True)
    with pytest.raises(FieldError, match="required"):
        field.clean("")


def test_email_and_url_rules_match_api_validation():
    with pytest.raises(FieldError):
        Email("contact").clean("not-an-email")
    assert Email("contact").clean("user@example.com") == "user@example.com"

    with pytest.raises(FieldError):
        URLField("site").validation_field().validate("not a url")
    assert url_validator is not None  # the exact factory the API uses


def test_length_range_pattern_and_choice_rules():
    assert Text("name", min_length=3).clean("abcd") == "abcd"
    with pytest.raises(FieldError):
        Text("name", min_length=3).clean("ab")
    with pytest.raises(FieldError):
        Number("age", minimum=0, maximum=120).clean(-1)
    with pytest.raises(FieldError):
        Slug("slug").clean("Not A Slug!")
    with pytest.raises(FieldError):
        Color("colour").clean("red")
    with pytest.raises(FieldError):
        Select("status", choices=[("draft", "Draft")]).clean("bogus")


def test_structured_fields_parse_json_and_reject_malformed_payloads():
    assert JSONField("meta").clean('{"a": 1}') == {"a": 1}
    with pytest.raises(FieldError):
        JSONField("meta").clean("{bad json")
    assert KeyValue("pairs").clean('{"k": "v"}') == {"k": "v"}
    assert Tags("tags").clean("one,two") == ["one", "two"]


def test_resource_validate_returns_cleaned_values_and_field_errors():
    class ProductResource(Resource):
        model = object
        fields: ClassVar[list[Field]] = [
            Text("name", required=True, min_length=2).searchable(),
            Email("contact"),
            Number("price", minimum=0).filterable(),
        ]

    resource = ProductResource()
    cleaned, errors = resource.validate({"name": "AB", "contact": "bad", "price": "-3"})
    assert "contact" in errors
    assert "price" in errors
    assert cleaned["name"] == "AB"

    cleaned, errors = resource.validate({"name": "Widget", "contact": "a@b.com", "price": "5"})
    assert errors == {}
    assert cleaned["price"] == 5


# --- output escaping and sanitization ---------------------------------------


def test_scalar_display_is_html_escaped():
    field = Text("title")
    rendered = field.display("<script>alert(1)</script>")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_markdown_display_sanitizes_html_and_dangerous_urls():
    field = Markdown("body")
    rendered = field.display("**hello** <script>bad()</script> [x](javascript:alert(1))")
    assert "<strong>hello</strong>" in rendered
    assert "<script>" not in rendered
    assert "javascript:" not in rendered


def test_badge_display_escapes_untrusted_label():
    field = Badge("status", choices=[("ok", "<b>OK</b>")])
    rendered = field.display("ok")
    assert "<b>" not in rendered


# --- resource options and schema augmentation --------------------------------


def test_resource_derives_legacy_admin_options():
    class OrderResource(Resource):
        model = object
        fields: ClassVar[list[Field]] = [
            Text("reference", required=True).searchable().sortable().show_on_index(),
            Email("buyer").show_on_index(),
            Select("status", choices=[("new", "New")]).filterable(),
            Number("total").readonly().show_on_index(),
            Text("notes").show_on_index(False).show_on_form(False).show_on_detail(False),
        ]

    options = OrderResource().to_options()
    assert options["fields"] == ["reference", "buyer", "status", "total", "notes"]
    assert options["search_fields"] == ["reference"]
    assert options["list_filter"] == ["status"]
    assert options["readonly_fields"] == ["total"]
    assert options["list_display"] == ["reference", "buyer", "status", "total"]
    assert "notes" not in options["fields_for_form"]


def test_augment_schema_exposes_help_and_dependency_metadata():
    class OrderResource(Resource):
        model = object
        fields: ClassVar[list[Field]] = [
            Text("kind").help("Physical or digital"),
            Text("sku").depends_on("kind", "digital"),
        ]

    schema = augment_schema({"kind": {"kind": "text"}, "sku": {"kind": "text"}}, OrderResource())
    assert schema["kind"]["help_text"] == "Physical or digital"
    assert schema["sku"]["depends_on"] == ("kind", "digital")
    assert schema["sku"]["label"] == "Sku"


def test_relation_fields_expose_prefetch_names():
    class OrderResource(Resource):
        model = object
        fields: ClassVar[list[Field]] = [
            BelongsTo("customer").show_on_index(),
            HasMany("lines").show_on_index(),
            ManyToMany("tags").show_on_index(False),
        ]

    resource = OrderResource()
    assert "customer" in resource.select_related_names()
    assert "lines" in resource.prefetch_related_names()
    assert "tags" not in resource.prefetch_related_names()
