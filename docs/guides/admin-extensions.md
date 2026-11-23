# Admin extensions with Teloce

An admin extension adds **custom fields, dashboard cards, tools and pages** to the
Flaxon admin. The UI is written as Teloce `.vel` single-file components, which are
compiled by `teloce-py` — Python only. Extension authors never need Node.js, npm,
a bundler, or a CDN at build or run time.

Extensions ship as ordinary Python packages named `flaxon-admin-*` and are found
through the `flaxon.admin` entry-point group.

## What the admin does for you

- Compiles every `ui/*.vel` file once at startup and serves it from
  `<admin>/extensions/assets/<name>.js` as a same-origin ES module.
- Renders cards and pages on the server first, then mounts the component in the
  browser (progressive enhancement).
- Escapes every prop it writes into HTML, and keeps the admin's session,
  permission and CSRF rules for extension pages.
- Registers one dashboard card per model that uses your field, through the
  `model_registered` hook.

## Build a custom field in about 20 lines

A field is a `TeloceField`: a normal `Field` (so validation, sorting and
permissions still work) plus a component and a plain-HTML fallback. The component
receives `name`, `label`, `required` and the current `value` as props, and must
render a real control carrying the `name` prop so the form submits.

```python
from flaxon.admin import Component, TeloceField

SENTIMENT = """
<template>
  <fieldset :data-field="name"><legend>{{ label }}</legend>
    <label v-for="option in options" :key="option.value"><input type="radio" :name="name" :value="option.value" @change="pick(option.value)">{{ option.label }}</label>
  </fieldset>
</template>
<script lang="ts">
export default { props: { name: String, label: String, value: String, options: Array }, methods: { pick(value: string) { this.value = value; this.$emit("change", value); } } };
</script>
"""


class SentimentField(TeloceField):
    def __init__(self, name, **options):
        choices = [("happy", "Happy"), ("neutral", "Neutral"), ("sad", "Sad")]
        super().__init__(name, Component("sentiment", SENTIMENT), fallback="select", fallback_choices=choices, **options)


field = SentimentField("sentiment", label="How was it?")
assert field.schema_entry()["component"] == "sentiment"
```

Use it exactly like a built-in field:

```python
from flaxon.admin.resources import Resource, Text


class Feedback:
    """Your Tortoise model, shown here as a placeholder."""


class FeedbackResource(Resource):
    model = Feedback
    fields = [Text("comment"), SentimentField("sentiment").sortable()]
```

`fallback="select"` (or `"text"` / `"number"`) keeps the form usable before the
bundle mounts and when JavaScript is disabled. Validate the value in Python by
overriding `validation_field()` or passing `rules(...)`; the browser is never the
only guard.

## Cards, pages and tools

```python
from flaxon.admin import AdminExtension, Component, ExtensionPage, TeloceCard, Tool

CARD = """<template><p class="signups">{{ data.value }} signups</p></template>"""
PAGE = """<template><h2>{{ title }}</h2><p>{{ models.length }} models</p></template>"""


class SignupsCard(TeloceCard):
    def __init__(self, model):
        super().__init__("Signups", Component("signups", CARD), calculate=self.count, model=model)

    async def count(self, request=None, *, now=None):
        return {"value": await self.model.all().count()}


class ReportsPage(ExtensionPage):
    def __init__(self):
        super().__init__("reports", Component("reports", PAGE), permission="admin.view_reports")


class AnalyticsExtension(AdminExtension):
    name = "analytics"
    label = "Analytics"

    def setup(self, dashboard):
        dashboard.register_permission("admin.view_reports", "View reports", category="Extensions")

    def pages(self):
        return [ReportsPage()]

    def tools(self):
        return [Tool("Reports", ReportsPage(), icon="fa-chart-line")]
```

- `TeloceCard` calculates in Python (SQL through the ORM) and passes a
  JSON-serialisable dict as the `data` prop. Rendering happens in the component.
- `ExtensionPage` is mounted through `AdminDashboard.add_view`, so it keeps the
  permission check, CSRF check and navigation entry. Set an explicit
  `permission` — `admin.view_dashboard` is the default.
- `Tool` is a dashboard shortcut to a page. It does no work on the index, so
  adding tools cannot slow the dashboard down.
- `model_registered(dashboard, admin_model)` runs for models registered *after*
  the extension loaded. Use it to add per-model cards; that is how the example
  plugin adds one card per rated model.

## Discovery and configuration

```python
from flaxon.admin import AdminConfig

config = AdminConfig(disabled_extensions=("analytics",))
assert config.enable_extensions and config.disabled_extensions == ("analytics",)
```

Only distributions whose name starts with `flaxon-admin-` are auto-discovered;
other entry points in the `flaxon.admin` group are ignored with a warning. Pass
explicit instances with `AdminConfig(extensions=[AnalyticsExtension()])`, or turn
discovery off entirely with `AdminConfig(enable_extensions=False)`.

## Package it

```toml
[project]
name = "flaxon-admin-analytics"
version = "0.1.0"
dependencies = ["flaxon>=0.3.2", "teloce-py>=0.3.4"]

[project.entry-points."flaxon.admin"]
analytics = "flaxon_admin_analytics:AnalyticsExtension"

[tool.setuptools.package-data]
flaxon_admin_analytics = ["ui/*.vel"]
```

Place components in `<package>/ui/`; `AdminExtension.component("name.vel")` resolves
them and refuses paths outside the package.

## The complete example plugin

`examples/flaxon_admin_rating` is a working `flaxon-admin-rating` package:

```python
from flaxon_admin_rating import RatingExtension, RatingField

extension = RatingExtension()
assert extension.name == "rating"
assert RatingField("rating").component.name == "rating"
```

It contributes a 1–5 star `RatingField`, an average/distribution `RatingCard`, a
"Rating insights" page and a dashboard tool, and registers the
`admin.view_ratings` permission. Install and run it:

```bash
cd examples/flaxon_admin_rating
python -m pip install -e .
python -m flaxon run app:app --port 8000
```

Open `http://127.0.0.1:8000/admin/login` and sign in with `admin` / `Admin123!`.
The Products form shows the star control, the dashboard shows the card and tool,
and `/admin/ratings` lists every rated model.

## Limits worth knowing

- **Teloce's static renderer interpolates text and repeats `v-for` blocks, but it
  does not evaluate dynamic attribute bindings** (`:name`, `:checked`,
  `:data-x`). Cards and pages therefore use interpolated attributes; form fields
  rely on the HTML fallback until the component mounts. The browser bundle applies
  the real bindings.
- **Extensions are trusted code.** They run inside your process and can import
  anything. Discovery is restricted to `flaxon-admin-*` packages, but installing
  one is a deliberate act. There is no sandbox.
- **Assets are same-origin and authenticated.** The bundle and components require
  a signed-in user with `admin.view_dashboard`; nothing is fetched from a CDN.
- **Props are data, not markup.** Values are JSON-encoded and HTML-escaped before
  they reach an attribute, and Teloce renders text through text nodes.
- The extension bundle is one ES module per component plus a small loader. It is
  loaded on every admin page (cached with an `ETag`), so keep components small.

## Verify it

```bash
python -m pytest tests/unit/test_admin_extensions.py \
  tests/integration/test_admin_extensions_api.py \
  tests/browser/test_admin_extensions_browser.py -q --no-cov -o addopts=""
python scripts/generate_admin_extension_docs.py --check
```

The browser test drives the real admin under uvicorn: it logs in, checks the
server-rendered card, opens the extension page, clicks a star, submits the form,
and asserts the saved value — with no console errors and no external requests.
