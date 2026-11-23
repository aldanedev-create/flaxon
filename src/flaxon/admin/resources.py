"""Declarative, additive Resource and Field API for the Flaxon admin.

A :class:`Resource` describes which model to expose and which fields to render.
Fields carry their own validation rules, widget hints, visibility flags and
fluent options. The API is deliberately independent of the legacy
``admin.register(Model, **options)`` path: registering a ``Resource`` simply
produces the same options the registry already understands, so every existing
admin feature keeps working unchanged.

Validation reuses :mod:`flaxon.validation` field objects, the same objects a
JSON API uses. Output is HTML-escaped by default; Markdown is additionally
sanitised with Flaxon's existing :class:`~flaxon.security.Sanitizer`.
"""

from __future__ import annotations

import html
import json
import re
from decimal import Decimal
from typing import Any, ClassVar

from flaxon.security import Sanitizer
from flaxon.validation import (
    AnyField,
    BoolField,
    ChoiceField,
    DateField,
    DateTimeField,
    DecimalField,
    EmailField,
    FieldError,
    FloatField,
    IntField,
    ListField,
    StrField,
    Validator,
    url_validator,
)

# Widget-kind constants. Plugins can declare a kind without importing a class.
TEXT = "text"
TEXTAREA = "textarea"
NUMBER = "number"
BOOLEAN = "checkbox"
SELECT = "select"
BADGE = "badge"
DATE = "date"
DATETIME = "datetime-local"
EMAIL = "email"
URL_KIND = "url"
PASSWORD = "password"
IMAGE = "image"
FILE = "file"
MARKDOWN = "textarea"
CODE = "textarea"
JSON_KIND = "textarea"
KEY_VALUE = "textarea"
TAG = "textarea"
SLUG = "text"
COLOR = "color"
CURRENCY = "number"
BELONGS_TO = "select"
HAS_MANY = "many"
MANY_TO_MANY = "many"

__all__ = [
    "BADGE",
    "BELONGS_TO",
    "BOOLEAN",
    "CODE",
    "COLOR",
    "CURRENCY",
    "DATE",
    "DATETIME",
    "EMAIL",
    "FILE",
    "HAS_MANY",
    "IMAGE",
    "JSON",
    "KEY_VALUE",
    "MANY_TO_MANY",
    "MARKDOWN",
    "NUMBER",
    "PASSWORD",
    "SELECT",
    "SLUG",
    "TAG",
    "TEXT",
    "TEXTAREA",
    "URL",
    "Badge",
    "BelongsTo",
    "Boolean",
    "Code",
    "Color",
    "Currency",
    "Date",
    "DateTime",
    "Email",
    "Field",
    "File",
    "HasMany",
    "Image",
    "KeyValue",
    "ManyToMany",
    "Markdown",
    "Number",
    "Password",
    "Resource",
    "Select",
    "Slug",
    "Tags",
    "Text",
    "Textarea",
    "augment_schema",
]

_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_COLOR_PATTERN = r"^#(?:[0-9a-fA-F]{3}){1,2}$"


class Field:
    """Base class for a declarative admin field.

    All fluent methods mutate and return ``self`` so declarations stay short.
    """

    kind: ClassVar[str] = TEXT

    def __init__(
        self,
        name: str,
        label: str | None = None,
        *,
        required: bool = False,
        default: Any = None,
        choices: list[Any] | tuple[Any, ...] | None = None,
        help_text: str = "",
        validators: list[Validator] | None = None,
        widget: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        pattern: str | None = None,
        index: bool = True,
        detail: bool = True,
        form: bool = True,
        sortable: bool = False,
        searchable: bool = False,
        filterable: bool = False,
        readonly: bool = False,
    ) -> None:
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self.required = required
        self.default = default
        self.choices = list(choices) if choices is not None else None
        self.help_text = help_text
        self.validators = list(validators or [])
        self.widget = widget
        self.min_length = min_length
        self.max_length = max_length
        self.minimum = minimum
        self.maximum = maximum
        self.pattern = pattern
        self.on_index = index
        self.on_detail = detail
        self.on_form = form
        self.is_sortable = sortable
        self.is_searchable = searchable
        self.is_filterable = filterable
        self.is_readonly = readonly
        self.depends: tuple[str, str] | None = None

    # -- fluent options ------------------------------------------------------
    def sortable(self, enabled: bool = True) -> Field:
        """Enable or disable sorting on the index."""
        self.is_sortable = enabled
        return self

    def searchable(self, enabled: bool = True) -> Field:
        """Enable or disable full-text search for this field."""
        self.is_searchable = enabled
        return self

    def filterable(self, enabled: bool = True) -> Field:
        """Enable or disable filtering on the change list."""
        self.is_filterable = enabled
        return self

    def readonly(self, enabled: bool = True) -> Field:
        """Mark this field read-only in forms."""
        self.is_readonly = enabled
        return self

    def rules(self, *validators: Validator) -> Field:
        """Attach framework validators to this field."""
        self.validators.extend(validators)
        return self

    def help(self, text: str) -> Field:
        """Set the help text shown beneath the control."""
        self.help_text = text
        return self

    def show_on_index(self, enabled: bool = True) -> Field:
        """Control whether this field appears on the index."""
        self.on_index = enabled
        return self

    def show_on_detail(self, enabled: bool = True) -> Field:
        """Control whether this field appears on the detail page."""
        self.on_detail = enabled
        return self

    def show_on_form(self, enabled: bool = True) -> Field:
        """Control whether this field appears in create/edit forms."""
        self.on_form = enabled
        return self

    def depends_on(self, field_name: str, value: str) -> Field:
        """Show this field only when another field has the given value."""
        self.depends = (field_name, value)
        return self

    # -- validation ----------------------------------------------------------
    def validation_field(self) -> Any:
        """Return the ``flaxon.validation`` field carrying the same rules."""
        validators = list(self.validators)
        if self.kind == "url":
            validators.append(url_validator())
        return StrField(
            required=self.required,
            default=self.default,
            validators=validators,
            min_length=self.min_length,
            max_length=self.max_length,
            pattern=self.pattern,
        )

    def clean(self, raw: Any) -> Any:
        """Validate and coerce a submitted value, raising ``FieldError``."""
        field = self.validation_field()
        value = field.deserialize(raw)
        field.validate(value)
        if self.required and (value is None or value == ""):
            raise FieldError("This field is required.")
        return self.coerce(value)

    def coerce(self, value: Any) -> Any:
        """Subclass hook for structured values. Default keeps the value."""
        return value

    # -- rendering -----------------------------------------------------------
    def display(self, value: Any) -> str:
        """Return an HTML-safe representation of *value*."""
        if value is None:
            return ""
        return html.escape(str(value))

    def schema_entry(self) -> dict[str, Any]:
        """Return the template-facing metadata for this field."""
        return {
            "kind": self.widget or self.kind,
            "label": self.label,
            "help_text": self.help_text,
            "depends_on": self.depends,
            "required": self.required,
            "default": "" if self.default is None else self.default,
            "choices": self._choice_pairs() or [],
            "widget": self.widget or "",
            "max_length": self.max_length,
            "min": self.minimum,
            "max": self.maximum,
            "pattern": self.pattern,
            "readonly": self.is_readonly,
        }

    def _choice_pairs(self) -> list[tuple[str, str]] | None:
        if self.choices is None:
            return None
        pairs = []
        for choice in self.choices:
            if isinstance(choice, (tuple, list)) and len(choice) == 2:
                pairs.append((str(choice[0]), str(choice[1])))
            else:
                pairs.append((str(choice), str(choice)))
        return pairs

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, kind={self.kind!r})"


class Text(Field):
    """The Text field type."""

    kind = TEXT


class Textarea(Field):
    """The Textarea field type."""

    kind = TEXTAREA


class Number(Field):
    """The Number field type."""

    kind = NUMBER

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        has_fraction = (self.minimum is not None and self.minimum % 1) or (
            self.maximum is not None and self.maximum % 1
        )
        if has_fraction:
            return FloatField(
                required=self.required,
                default=self.default,
                validators=list(self.validators),
                minimum=self.minimum,
                maximum=self.maximum,
            )
        return IntField(
            required=self.required,
            default=self.default,
            validators=list(self.validators),
            minimum=int(self.minimum) if self.minimum is not None else None,
            maximum=int(self.maximum) if self.maximum is not None else None,
        )


class Boolean(Field):
    """The Boolean field type."""

    kind = BOOLEAN

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return BoolField(required=self.required, default=self.default, validators=list(self.validators))


class Select(Field):
    """The Select field type."""

    kind = SELECT

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        choices = [pair[0] for pair in self._choice_pairs() or []]
        return ChoiceField(
            choices=choices,
            required=self.required,
            default=self.default,
            validators=list(self.validators),
        )


class Badge(Select):
    """The Badge field type."""

    kind = BADGE

    def display(self, value: Any) -> str:
        """Render an HTML-safe value for the admin."""
        pairs = dict(self._choice_pairs() or [])
        return html.escape(str(pairs.get(str(value), value)))


class Date(Field):
    """The Date field type."""

    kind = DATE

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return DateField(required=self.required, default=self.default, validators=list(self.validators))


class DateTime(Field):
    """The DateTime field type."""

    kind = DATETIME

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return DateTimeField(required=self.required, default=self.default, validators=list(self.validators))


class Email(Field):
    """The Email field type."""

    kind = EMAIL

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return EmailField(required=self.required, default=self.default, validators=list(self.validators))


class URL(Field):
    """The URL field type."""

    kind = URL_KIND


class Password(Field):
    """The Password field type."""

    kind = PASSWORD

    def display(self, value: Any) -> str:
        """Render an HTML-safe value for the admin."""
        return "••••••••" if value else ""


class Image(URL):
    """The Image field type."""

    kind = IMAGE

    def display(self, value: Any) -> str:
        """Render an HTML-safe value for the admin."""
        if not value:
            return ""
        return f'<img src="{html.escape(str(value), quote=True)}" alt="">'


class File(Field):
    """The File field type."""

    kind = FILE


class Markdown(Field):
    """The Markdown field type."""

    kind = MARKDOWN

    def display(self, value: Any) -> str:
        """Render an HTML-safe value for the admin."""
        if value is None:
            return ""
        text = html.escape(str(value), quote=False)

        def replace_link(match: re.Match[str]) -> str:
            label, target = match.group(1), match.group(2).strip()
            if not target.lower().startswith(("http://", "https://", "mailto:")):
                return label
            return f'<a href="{html.escape(target, quote=True)}" rel="noreferrer">{label}</a>'

        text = _MARKDOWN_LINK.sub(replace_link, text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        return Sanitizer.allow_html(text)


class Code(Field):
    """The Code field type."""

    kind = CODE

    def display(self, value: Any) -> str:
        """Render an HTML-safe value for the admin."""
        if value is None:
            return ""
        return f"<code>{html.escape(str(value))}</code>"


class JSON(Field):
    """The JSON field type."""

    kind = JSON_KIND

    def coerce(self, value: Any) -> Any:
        """Convert a validated value into its final Python form."""
        if value is None or value == "":
            return None
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError) as exc:
            raise FieldError("Enter valid JSON.") from exc

    def display(self, value: Any) -> str:
        """Render an HTML-safe value for the admin."""
        return html.escape(json.dumps(value, ensure_ascii=False, default=str) if value is not None else "")


class KeyValue(JSON):
    """The KeyValue field type."""

    kind = KEY_VALUE

    def coerce(self, value: Any) -> Any:
        """Convert a validated value into its final Python form."""
        parsed = super().coerce(value)
        if parsed is None:
            return None
        if not isinstance(parsed, dict):
            raise FieldError("Expected a JSON object of key/value pairs.")
        return parsed


class Tags(Field):
    """The Tags field type."""

    kind = TAG

    def coerce(self, value: Any) -> Any:
        """Convert a validated value into its final Python form."""
        if value is None or value == "":
            return []
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        return [part.strip() for part in str(value).split(",") if part.strip()]

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return ListField(
            item_field=StrField(),
            required=self.required,
            default=self.default,
            validators=list(self.validators),
        )

    def clean(self, raw: Any) -> Any:
        """Validate and coerce a submitted value."""
        # The browser submits a comma-separated string; normalise it before the
        # shared ListField validation so rules apply to the final list value.
        if isinstance(raw, str):
            raw = [part.strip() for part in raw.split(",") if part.strip()]
        return super().clean(raw)


class Slug(Field):
    """The Slug field type."""

    kind = SLUG

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return StrField(
            required=self.required,
            default=self.default,
            validators=list(self.validators),
            pattern=self.pattern or _SLUG_PATTERN,
        )


class Color(Field):
    """The Color field type."""

    kind = COLOR

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return StrField(
            required=self.required,
            default=self.default,
            validators=list(self.validators),
            pattern=self.pattern or _COLOR_PATTERN,
        )


class Currency(Field):
    """The Currency field type."""

    kind = CURRENCY

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return DecimalField(
            required=self.required,
            default=self.default,
            validators=list(self.validators),
            minimum=Decimal(str(self.minimum)) if self.minimum is not None else None,
            maximum=Decimal(str(self.maximum)) if self.maximum is not None else None,
            places=2,
        )


class BelongsTo(Field):
    """A searchable async select for a foreign-key relation."""

    kind = BELONGS_TO

    def __init__(
        self,
        name: str,
        label: str | None = None,
        *,
        related_model: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, label, **kwargs)
        self.related_model = related_model

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return AnyField(required=self.required, default=self.default, validators=list(self.validators))


class HasMany(Field):
    """A related table with inline creation for a reverse FK relation."""

    kind = HAS_MANY

    def __init__(
        self,
        name: str,
        label: str | None = None,
        *,
        related_model: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, label, **kwargs)
        self.related_model = related_model

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return AnyField(required=False, validators=list(self.validators))


class ManyToMany(Field):
    """Attach/detach relations, optionally carrying pivot fields."""

    kind = MANY_TO_MANY

    def __init__(
        self,
        name: str,
        label: str | None = None,
        *,
        related_model: Any = None,
        pivot_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, label, **kwargs)
        self.related_model = related_model
        self.pivot_fields = list(pivot_fields or [])

    def validation_field(self) -> Any:
        """Build the equivalent flaxon.validation field."""
        return AnyField(required=False, validators=list(self.validators))


class Resource:
    """Describe a model as a full admin in a handful of lines."""

    model: ClassVar[Any] = None
    fields: ClassVar[list[Field]] = []
    name: ClassVar[str | None] = None

    def __init__(self) -> None:
        object.__setattr__(self, "fields", list(type(self).fields))

    def get_field(self, name: str) -> Field | None:
        """Return the declared field with the given name."""
        return next((field for field in self.fields if field.name == name), None)

    def field_names(self) -> list[str]:
        """Return all declared field names."""
        return [field.name for field in self.fields]

    def to_options(self) -> dict[str, Any]:
        """Translate the declaration into options the legacy registry accepts."""
        return {
            "fields": self.field_names(),
            "fields_for_form": [field.name for field in self.fields if field.on_form],
            "list_display": [field.name for field in self.fields if field.on_index],
            "search_fields": [field.name for field in self.fields if field.is_searchable],
            "list_filter": [field.name for field in self.fields if field.is_filterable],
            "readonly_fields": [field.name for field in self.fields if field.is_readonly],
            "name": self.name or type(self).__name__.removesuffix("Resource").lower(),
            "resource": self,
        }

    def validate(self, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        """Validate submitted form data; return ``(cleaned, errors)``."""
        cleaned: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for field in self.fields:
            if not field.on_form or field.is_readonly:
                continue
            raw = data.get(field.name)
            if raw is None and not field.required and field.name not in data:
                continue
            try:
                cleaned[field.name] = field.clean(raw)
            except FieldError as exc:
                errors[field.name] = exc.message
        return cleaned, errors

    def select_related_names(self) -> list[str]:
        """BelongsTo columns shown on the index can be JOINed in one query."""
        return [field.name for field in self.fields if isinstance(field, BelongsTo) and field.on_index]

    def prefetch_related_names(self) -> list[str]:
        """Multi-valued relations shown on the index must be prefetched."""
        return [
            field.name for field in self.fields if isinstance(field, (HasMany, ManyToMany)) and field.on_index
        ]


def augment_schema(schema: dict[str, Any], resource: Resource | None) -> dict[str, Any]:
    """Expose resource field metadata to the existing admin templates."""
    if resource is None:
        return schema
    for field in resource.fields:
        entry = dict(schema.get(field.name, {}))
        metadata = field.schema_entry()
        for key, value in metadata.items():
            if key == "required" and not value and entry.get("required"):
                continue  # the ORM adapter knows more about nullability
            if value is not None:
                entry[key] = value
        if field.on_index is False or field.on_form is False:
            entry["visible_in_form"] = field.on_form
        schema[field.name] = entry
    return schema
