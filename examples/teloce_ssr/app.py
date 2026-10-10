"""Small SSR and development-debugger example using HTML components."""

import os
from pathlib import Path

from flaxon import Flaxon, Request

ROOT = Path(__file__).resolve().parent
app = Flaxon("SSR projects", debug=os.getenv("FLAXON_DEBUG", "1") == "1")
app.use_teloce(project_root=ROOT, options={"ssr": "opt-in"})


@app.get("/")
async def home(request: Request):
    public_props = {
        "title": "Your projects",
        "count": {"value": 2},
        "projects": [
            {"id": 1, "name": "Learn Flaxon"},
            {"id": 2, "name": "Build with Teloce"},
        ],
    }
    return await request.compile(
        "app.html",
        public_props,
        ssr=True,
        meta={"title": "Projects", "description": "A Flaxon and Teloce SSR example"},
    )


@app.get("/api/example-error")
async def example_error():
    raise RuntimeError("Example API failure for the development dashboard")
