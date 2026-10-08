"""Compose modules here; settings and commands are shared with management.py."""
from flaxon import Flaxon, Request
from flaxon.db.admin import configure_admin
from flaxon.jinax import Jinax
from modules.welcome.module import welcome


def create_app():
    app = Flaxon.from_settings()
    app.mount_module(welcome, prefix="/api/welcome")

    # Management discovers the same mounts without compiling UI or opening AdminStore.
    if app.is_management:
        return app

    settings = app.settings
    app.mount_static("/assets", str(settings.root / "public"))
    app.use_templates(Jinax(str(settings.root / "templates"), auto_reload=settings.DEBUG))
    configure_admin(app)
    app.use_teloce(
        project_root=settings.root,
        ui_dir="ui",
        title=f"Welcome to {settings.PROJECT_NAME}",
        favicon="https://flaxon-website.vercel.app/assets/images/logo/flaxon.png",
        description="Your Python and Teloce full-stack application is ready.",
        stylesheets=["/assets/app.css"],
        options={"minifier": "minifyjs"},
    )

    @app.get("/")
    async def home(request: Request):
        return await request.compile("app.html", {"project_name": settings.PROJECT_NAME})

    @app.get("/server-page")
    async def server_page(request: Request):
        return await app.jinax.render_response("welcome.html", {"project_name": settings.PROJECT_NAME})

    return app


app = create_app()
