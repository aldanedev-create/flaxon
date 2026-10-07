"""Application composition: mount modules, Jinax pages, Teloce UI, and protected admin."""

from flaxon import Flaxon, Request
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.services import AdminStore
from flaxon.jinax import Jinax
from flaxon.database.adapters.sqlite import SQLiteAdapter
from flaxon.database.manager import DatabaseManager

from modules.welcome.module import welcome
from settings import ROOT, DATA_DIR, DATABASE_PATH, PROJECT_NAME, DEBUG


def create_app():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app = Flaxon(PROJECT_NAME, debug=DEBUG, openapi=True)

# openapi=True
#This registers:
#| URL | Purpose |
#|---|---|
#| `/openapi.json` | Generated OpenAPI 3.1 document |
#| `/docs` | Interactive Swagger UI with Try it out |
#| `/redoc` | ReDoc reference browser |


    database = DatabaseManager(SQLiteAdapter(database=str(DATABASE_PATH)))
    app.container.register_instance("db", database)
    app.on_startup(database.initialize)
    app.on_shutdown(database.close)
    app.mount_module(welcome, prefix="/api/welcome")
    app.mount_static("/assets", str(ROOT / "public"))

    # Jinax can power your entire website, or coexist with a Teloce interface.
    app.use_templates(Jinax(str(ROOT / "templates"), auto_reload=DEBUG))

    # The admin has its own server-rendered interface and persistent accounts.
    AdminDashboard(
        app,
        config=AdminConfig(site_title=f"{PROJECT_NAME} admin", index_title="Welcome to your Flaxon admin"),
        store=AdminStore(str(DATABASE_PATH)),
        users=[],
        upload_dir=str(DATA_DIR / "uploads"),
        strict_permissions=True,
        microservices=False,
    )
    app.use_teloce(
        project_root=ROOT,
        ui_dir="ui",
        title=f"Welcome to {PROJECT_NAME}",
        favicon="https://flaxon-website.vercel.app/assets/images/logo/flaxon.png",
        description="Your Python and Teloce full-stack application is ready.",
        stylesheets=["/assets/app.css"],
        options={"minifier": "minifyjs"},
    )

    @app.get("/")
    async def home(request: Request):
        return await request.compile("app.html", {"project_name": PROJECT_NAME})

    @app.get("/server-page")
    async def server_page(request: Request):
        return await app.jinax.render_response("welcome.html", {"project_name": PROJECT_NAME})

    return app


app = create_app()
