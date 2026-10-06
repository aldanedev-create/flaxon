# Flaxon

![Flaxon](assets/flaxon.png)

**Python on the server. Teloce in the browser. One full-stack project.**

Build interactive web apps with Python routes, APIs and WebSockets alongside
Teloce pages, reusable components and scoped styles. Write the UI in `.html` or
`.vel`, with JavaScript or `<script lang="ts">` and imported `.ts` helpers.
Keep a feature's endpoints and interface together in a Flaxon module.

```bash
pip install "flaxon[standard]"
```

```python
from pathlib import Path
from flaxon import Flaxon, Request

app = Flaxon("Taskboard", debug=True)
app.use_teloce(project_root=Path(__file__).parent, ui_dir="ui")

@app.get("/")
async def home(request: Request):
    return await request.compile("app.html", {"title": "My tasks"})
```

Teloce compiles your interface to browser JavaScript. MinifyJS optimizes production
output without Node. Prefer server-rendered pages? Use Flaxon's Jinax templates.
API-only apps and other frontends also work.

[Quick start](docs/quickstart.md) · [10 full-stack lessons](docs/fullstack/index.md) ·
[TypeScript/CDN example](examples/teloce_head_ts) · [API reference](docs/api/application.md) ·
[Changelog](CHANGELOG.md)
