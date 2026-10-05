# Flaxon

**Simple Python. Backend APIs and integrated Teloce interfaces.**

Flaxon is an async-first ASGI framework for APIs, WebSockets and web applications.
Use its module system to keep backend endpoints and Teloce pages together, or
choose your own frontend and database. Jinax templates, validation, OpenAPI,
Admin/CMS and optional integrations support larger applications.

## Install

Python 3.11+:

```bash
pip install "flaxon[standard]"
```

## API

```python
from flaxon import Flaxon

app = Flaxon("hello", debug=True)

@app.get("/api/hello")
async def hello():
    return {"message": "Hello from Flaxon"}
```

Run with `flaxon run app:app --reload`.

## Teloce UI

```python
from pathlib import Path
from flaxon import Request

app.use_teloce(project_root=Path(__file__).parent, ui_dir="ui")

@app.get("/")
@app.get("/<path:spa_path>")
async def page(request: Request, spa_path: str = ""):
    return await request.compile("app.html", {"business": "My business"})
```

Write components in `ui/app.html` and pages in `ui/pages/`. Flaxon compiles them
at startup, serves the JavaScript and connects Teloce's browser router. With the
updated Teloce integration, MinifyJS optimizes production output without Node.
Development keeps readable code and source maps. Authentication and persistent
storage remain application responsibilities.

[API and five lessons](docs/api/teloce.md) · [SiteLedger](examples/teloce_siteledger) ·
[Modules shop](examples/teloce_modules_shop) · [Documentation](docs/index.md) ·
[Changelog](CHANGELOG.md) · [License](LICENSE)
