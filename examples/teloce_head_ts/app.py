"""A small full-stack unit converter with TypeScript and optional CDN styling."""
from pathlib import Path

from flaxon import Flaxon, Request

root = Path(__file__).resolve().parent
app = Flaxon("Pocket Converter", debug=True)
app.mount_static("/static", str(root / "public"))

bootstrap_css = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
bootstrap_js = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
app.use_teloce(
    project_root=root,
    ui_dir="ui",
    entry="app.vel",
    title="Pocket Converter",
    favicon="/static/favicon.svg",
    description="A Flaxon and Teloce TypeScript example.",
    lang="en",
    theme_color="#101827",
    stylesheets=[bootstrap_css],
    scripts=[{"src": bootstrap_js, "defer": True}],
)

@app.get("/api/about")
async def about():
    return {"message": "Python serves the API; Teloce runs the interface."}

@app.get("/")
async def home(request: Request):
    return await request.compile("app.vel")
