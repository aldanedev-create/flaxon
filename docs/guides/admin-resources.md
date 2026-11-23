# Declarative admin resources

A `Resource` turns a model into a full admin without hand-writing views. It is
**additive**: `admin.register(Model, list_display=[...], ...)` keeps working
exactly as before, and every option below maps onto the existing registry.

## A model becomes an admin in under ten lines

```python
from flaxon.admin.resources import Resource, Text, Email

class CustomerResource(Resource):
    model = Customer
    fields = [Text("name", required=True).searchable(), Email("email")]

dashboard.register(CustomerResource)
```

`dashboard.register(CustomerResource)` derives `fields`, `list_display`,
`search_fields`, `list_filter`, `readonly_fields` and the admin URL name from
the declaration. The generated routes are the same ones the legacy registry
uses: `/admin/customer`, `/admin/customer/add`, `/admin/customer/<id>/edit`.

## Fields, options and server-side rules

Every field validates on the server with the same `flaxon.validation` field the
JSON API uses. Declarations stay readable because options are fluent:

```python
from flaxon.admin.resources import Resource, Number, Select, Text

class OrderResource(Resource):
    model = Order
    fields = [
        Text("reference", required=True, min_length=3).searchable().sortable(),
        Select("status", choices=[("new", "New"), ("paid", "Paid")]).filterable(),
        Number("total", minimum=0).help("Order value").show_on_index(),
        Text("internal_note").readonly().show_on_form(False),
    ]

cleaned, errors = OrderResource().validate(
    {"reference": "ORD-1", "status": "new", "total": "42"}
)
assert errors == {}
assert cleaned["total"] == 42
```

Available fluent options: `sortable()`, `searchable()`, `filterable()`,
`readonly()`, `rules(*validators)`, `help(text)`, `show_on_index()`,
`show_on_detail()`, `show_on_form()`, and `depends_on(field, value)`.
`depends_on` hides and disables a control until another field has the required
value; the server still validates every submitted field.

## Field catalogue

| Group | Fields |
|---|---|
| Text | `Text`, `Textarea`, `Slug`, `Password`, `Code`, `Markdown` (sanitized) |
| Numbers and choices | `Number`, `Currency`, `Boolean`, `Select`, `Badge`, `Color` |
| Dates and media | `Date`, `DateTime`, `Image`, `File` |
| Structured | `JSON`, `KeyValue`, `Tags` |
| Relations | `BelongsTo` (async searchable select), `HasMany` (related table + create), `ManyToMany` (attach/detach with `pivot_fields`) |

Output is HTML-escaped by default. `Markdown` additionally sanitizes HTML and
strips dangerous URL schemes using Flaxon's existing `Sanitizer`.

## Relations and the N+1 guard

Index columns that follow relations are loaded eagerly, so a page of records
does not issue one query per row:

```python
from flaxon.admin.resources import Resource, BelongsTo, HasMany, Text

class OrderResource(Resource):
    model = Order
    fields = [
        Text("reference").show_on_index(),
        BelongsTo("customer").show_on_index(),
        HasMany("lines").show_on_index(),
    ]

assert OrderResource().select_related_names() == ["customer"]
assert OrderResource().prefetch_related_names() == ["lines"]
```

`BelongsTo` columns use `select_related`; `HasMany` and `ManyToMany` columns use
`prefetch_related`. A query-count regression test asserts the statement count
stays bounded as the number of rows grows.

## Validation failures

A failed form re-renders with per-field messages and writes nothing:

```python
from flaxon.admin.resources import Resource, Email, Text

class SignupResource(Resource):
    model = Customer
    fields = [Text("name", required=True), Email("email")]

cleaned, errors = SignupResource().validate({"name": "A", "email": "bad"})
assert "email" in errors
```
