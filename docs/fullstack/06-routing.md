# Lesson 6: Add pages and direct-link navigation

Create `ui/pages/Tasks.html` and `ui/pages/tasks/[id].html`. The integration
builds a shared browser router; dynamic parameters become page props. Use a
root shell with marked links and an outlet:

```html
<nav><a href="/tasks" data-teloce-link>Tasks</a></nav>
<main data-teloce-router-view></main>
```

The root shell mounts the router; a detail page fetches its data by the `id`
prop. Register a server fallback after API routes:

```python
@app.get("/")
@app.get("/<path:spa_path>")
async def page(request: Request, spa_path: str = ""):
    return await request.compile("app.html")
```

Use an explicit API not-found response for unknown API paths so a catch-all
does not turn an API typo into a successful HTML response. External links,
downloads and modified clicks should retain normal browser behavior. Browser
navigation guards improve flow but cannot enforce server authorization.

**Checkpoint:** navigate to a detail page, refresh it, paste its address into a
new tab, and use Back/Forward. A route that only works after clicking inside the
app is missing server fallback behavior. Test unknown API and client paths too.


## Alternative: server HTML with Jinax

Not every page needs a client-rendered component. A public report or printable
invoice can use Jinax while the dashboard uses Teloce in the same app.

```python
from flaxon.jinax import Jinax

app.use_templates(Jinax(project_root / "templates"))

@app.get("/report")
async def report(request: Request):
    return await request.render("report.html", {"title": "Task report"})
```

Create `templates/report.html`:

```html
<!doctype html>
<html lang="en">
  <head><title>{{ title }}</title></head>
  <body><h1>{{ title }}</h1></body>
</html>
```

Register this server route before a broad SPA fallback. Jinax's Jinja2 environment
provides inheritance, includes, macros, filters and escaping; it does not compile
a Teloce SFC just because a template has an `.html` extension.

For a small reactive enhancement in a server-rendered page, use Teloce's
[standalone runtime](https://github.com/aldanedev-create/teloce-py/blob/main/docs/standalone-runtime.md).
Serve its packaged browser modules through your static mount. Use one intended
runtime path rather than accidentally loading both standalone and compiled app
runtimes for the same DOM tree. SSR output, compiled browser components and
standalone enhancement are separate patterns.


[Course contents](index.md) · [Previous lesson](05-head-and-cdn.md) · [Next lesson](07-modules.md)
