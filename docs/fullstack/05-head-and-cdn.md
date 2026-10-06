# Lesson 5: Configure the document head and CDN resources

Keep metadata in Python and application markup in Teloce:

```python
app.mount_static("/static", str(project_root / "public"))
app.use_teloce(
    project_root=project_root, title="Taskboard", ui_dir="ui",
    favicon="/static/favicon.svg", description="Track your team's tasks.",
    lang="en", theme_color="#101827",
    stylesheets=["https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"],
    scripts=[{"src": "/static/help.js", "defer": True}],
)
```

All extra settings are optional. The local icon must exist under the static
mount. Resource configuration emits links; it does not copy resources or put
your build on a CDN. Extra stylesheets follow compiled CSS, so inspect overrides.
CDN scripts have page privileges: use trusted providers, pin versions and
verified SRI attributes where practical. Do not load a second Teloce runtime.

Avoid relying on an async script being ready in `mounted()`. Coordinate library
readiness explicitly or use a bundled/local module when it is essential.
For offline desktop applications, ship local fonts and assets. CSP also needs
to account for the generated inline module bootstrap.

**Checkpoint:** inspect head tags, load the favicon, then disconnect networking.
Confirm which external enhancements fail and that the core workflow remains
usable. See the [resource attribute reference](../api/teloce.md).


## Keep CDN configuration outside component code

The [converter](../../examples/teloce_head_ts/app.py) shows two separately named
CDN variables. Multiple `cdn = ...` assignments overwrite one Python variable.
Use lists when loading several resources:

```python
stylesheets = ["/static/base.css", theme_cdn]
scripts = [
    {"src": library_cdn, "defer": True},
    {"src": "/static/help.js", "type": "module"},
]
```

This fragment assumes `theme_cdn` and `library_cdn` contain pinned, trusted URLs.
The module script can import browser modules; it cannot import Python or serve
untranspiled TypeScript. No `async` execution order is guaranteed. If the page
requires a third-party global, explicitly wait for readiness and show failure
state. The converter's Bootstrap data attributes work independently of its
Teloce calculation helper.

## Verify the page, not just the configuration

Inspect `html[lang]`, the title, icon link, description and theme-color metadata.
Fetch each local URL and verify external library behavior. The repository's
Chromium test converts miles using generated TypeScript output and opens a
Bootstrap collapse using the CDN script. Resource links alone do not prove that
an external library loaded or executed.


[Course contents](index.md) · [Previous lesson](04-typescript.md) · [Next lesson](06-routing.md)
