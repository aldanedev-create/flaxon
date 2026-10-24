"""Discord-clone example application factory.

Wires together the four Flaxon subsystems this course teaches:

- **flaxon.db**       durable domain models + migrations (models.py).
- **flaxon.modules**  composable route bundles (modules/), each declaring the
                      app collaborators it needs via ``requires("ctx")``.
- **flaxon.admin**    staff moderation of users/servers/messages (admin.py).
- **flaxon.cms**      an editorial "announcements" content type.
- **teloce**          the browser SPA (ui/) that talks to the JSON API.

Teloce is configured before the management guard so build/typecheck commands
still work; Admin/CMS/modules are only built for the live app.

    python management.py migrate
    python management.py setup-admin
    python seed.py            # optional: demo data
    python management.py runserver
"""
from __future__ import annotations

from flaxon import Flaxon, Request
from flaxon.admin.cms import CMSField, ContentType
from flaxon.db.admin import configure_admin

from admin import register as register_admin_models
from context import AppContext
from modules import accounts, bots, messages, realtime, servers
from settings import *  # noqa: F401,F403  (brings settings into module scope for from_settings)


def create_app() -> Flaxon:
    app = Flaxon.from_settings()
    settings = app.settings

    app.mount_static("/static", str(settings.root / "static"))
    # Teloce must be configured before the management guard so build/typecheck
    # commands can still compile the SPA.
    app.use_teloce(
        project_root=settings.root,
        ui_dir="ui",
        title="Discord Clone — System Design Course",
        description="A teaching Discord clone built on Flaxon + Teloce.",
    )

    # Management mode only needs settings, models and migrations; skip the rest.
    if app.is_management:
        return app

    # -- broadcaster: Redis in production, in-memory for dev/tests -----------
    if getattr(settings, "REDIS_URL", ""):
        from services.broadcaster import RedisBackedBroadcaster

        broadcaster = RedisBackedBroadcaster(settings.REDIS_URL)
    else:
        from services.broadcaster import MemoryBroadcaster

        broadcaster = MemoryBroadcaster()

    ctx = AppContext(secret_key=settings.SECRET_KEY, broadcaster=broadcaster)
    # Modules declare requires("ctx"); register it before mounting them.
    app.container.register_instance("ctx", ctx)
    app.on_startup(ctx.startup)
    app.on_shutdown(ctx.shutdown)

    # -- Admin: staff moderation over the ORM tables -------------------------
    admin = configure_admin(app)
    register_admin_models(admin)

    # -- CMS: an editorial "announcements" channel ---------------------------
    cms = app.cms
    cms.register(
        ContentType(
            name="announcement",
            label="Announcement",
            label_plural="Announcements",
            fields=[
                CMSField("title", "Title", required=True),
                CMSField("body", "Body", type="richtext", required=True),
                CMSField("pinned", "Pin to top", type="boolean"),
                CMSField(
                    "status",
                    "Status",
                    type="select",
                    choices=["draft", "published"],
                ),
            ],
            list_display=["title", "pinned", "status", "updated_at"],
            list_filter=["status", "pinned"],
            search_fields=["title", "body"],
        )
    )

    # -- JSON API modules ----------------------------------------------------
    app.mount_module(accounts, prefix="/api/auth")
    app.mount_module(servers, prefix="/api/servers")
    app.mount_module(messages, prefix="/api/channels")
    app.mount_module(bots, prefix="/api/bots")
    app.mount_module(realtime, prefix="")  # websocket route at /ws

    # -- SPA shell (last, so /api /admin /_flaxon win) ----------------------
    # The catch-all only serves the SPA for non-API paths; API/admin/asset
    # requests that miss a concrete route fail cleanly instead of returning HTML.
    @app.get("/")
    @app.get("/<path:spa_path>")
    async def spa(request: Request, spa_path: str = "") -> object:
        if spa_path.startswith(("api/", "admin", "_flaxon", "static")):
            from flaxon.exceptions import NotFound

            raise NotFound("Not found")
        return await request.compile(
            "app.html",
            {"title": "Discord Clone", "admin_url": "/admin/", "cms_url": "/admin/cms/"},
        )

    return app


app = create_app()
