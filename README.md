# Flaxon

![Flaxon logo](assets/flaxon.png)

**Simple Python. Complete web applications.**

Flaxon is an async-first Python full-stack framework: build HTTP APIs,
WebSockets and interactive Teloce interfaces in one project. Keep endpoints,
pages and components together with feature modules. Use Jinax for server-rendered
HTML, or integrate another frontend when needed.

```bash
pip install "flaxon[standard]"
```

```python
from pathlib import Path
from flaxon import Flaxon, Request

app = Flaxon("Hello", debug=True)
app.use_teloce(project_root=Path(__file__).parent, ui_dir="ui", title="Hello")

@app.get("/")
async def home(request: Request):
    return await request.compile("app.html", {"message": "Hello from Python"})
```

Create `ui/app.html` with `<template><h1>{{ message }}</h1></template>` and
`<script>export default { props: ["message"] };</script>`, then run
`flaxon run app:app --reload`.

Teloce compiles components to browser JavaScript; MinifyJS optimizes production
output. TypeScript components and modules are supported by compatible Teloce
versions. The integrated UI is client-rendered; Jinax provides server templates.

[Quick start](docs/quickstart.md) · [10 full-stack lessons](docs/fullstack/index.md) ·
[Head settings and API](docs/api/teloce.md) ·
[TypeScript/CDN example](examples/teloce_head_ts) ·
[Documentation](docs/index.md) · [Changelog](CHANGELOG.md) · [License](LICENSE)
