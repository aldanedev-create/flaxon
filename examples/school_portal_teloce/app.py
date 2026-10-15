"""Northstar Academy with a Teloce interface reading flaxon.db (Tortoise) models.

    python management.py migrate
    python management.py setup-admin
    python seed.py
    python management.py runserver

The public site is a single Teloce SPA (see `ui/`). It talks to the JSON API in
`modules/portal.py`, which reads the same ORM tables and CMS content that the
staff Admin edits. `app.use_teloce()` is configured before the management guard
so build/typecheck commands still work.
"""
from __future__ import annotations

from flaxon import Flaxon, Request
from flaxon.admin.cms import CMSField, ContentType
from flaxon.config import env
from flaxon.db.admin import configure_admin
from flaxon.jinax.loaders import CompositeLoader, FileSystemLoader

from models import Course, Enrollment, Staff, Student
from modules.portal import portal

NEWS_FIELDS = [
    CMSField("title", "Title", required=True),
    CMSField("summary", "Summary", required=True),
    CMSField(
        "category",
        "Category",
        type="select",
        choices=["Community", "Academics", "Arts & culture", "Athletics"],
        required=True,
    ),
    CMSField("body", "Body", type="richtext"),
    CMSField("status", "Status", type="select", choices=["draft", "published", "archived"]),
]

EVENT_FIELDS = [
    CMSField("title", "Title", required=True),
    CMSField("date", "Date", type="date", required=True),
    CMSField("time", "Time", type="text"),
    CMSField("location", "Location", type="text", required=True),
    CMSField(
        "category",
        "Category",
        type="select",
        choices=["Community", "Academics", "Arts & culture", "Athletics"],
        required=True,
    ),
    CMSField("description", "Description", type="textarea"),
    CMSField("status", "Status", type="select", choices=["draft", "published", "archived"]),
]


def create_app():
    app = Flaxon.from_settings()
    settings = app.settings

    # Trust a reverse proxy (GitHub Codespaces, a tunnel, Docker) for
    # X-Forwarded-Proto / X-Forwarded-Host so the Teloce development diagnostics
    # see the browser's real https origin instead of the internal
    # http://localhost. OFF by default — enable in development only via
    # FLAXON_TRUST_PROXY=1. NOTE: Flaxon's TrustedHostsMiddleware does not treat
    # "*" as a wildcard, so you must still list the public host in
    # FLAXON_ALLOWED_HOSTS (e.g. ${CODESPACE_NAME}-8000.app.github.dev).
    if env.bool("FLAXON_TRUST_PROXY", default=False):
        from flaxon.middleware import ProxyHeadersMiddleware

        app.add_middleware(ProxyHeadersMiddleware, trusted_proxies=["*"])

    app.mount_static("/school-static", str(settings.root / "static"))
    # Teloce must be configured before the management guard so that build and
    # typecheck commands can still compile the SPA.
    app.use_teloce(
        project_root=settings.root,
        ui_dir="ui",
        title="Northstar Academy",
        favicon="/school-static/favicon.svg",
        description="Northstar Academy: students, courses, and campus news.",
    )

    # Management mode only needs settings, models and migrations: it skips
    # templates, Admin and CMS so commands never open the AdminStore.
    if app.is_management:
        return app

    admin = configure_admin(app)
    # Let custom Admin pages render the project's templates too.
    admin.jinax.environment.loader = CompositeLoader(
        [FileSystemLoader(str(settings.root / "templates")), admin.jinax.environment.loader]
    )
    cms = app.cms
    cms.register(
        ContentType(
            name="news",
            label="News item",
            label_plural="News",
            fields=NEWS_FIELDS,
            list_display=["title", "status", "updated_at"],
            list_filter=["status"],
            search_fields=["title", "summary", "body"],
        )
    )
    cms.register(
        ContentType(
            name="events",
            label="School event",
            label_plural="Events",
            fields=EVENT_FIELDS,
            list_display=["title", "date", "location", "status"],
            list_filter=["status", "category"],
            search_fields=["title", "location", "description"],
        )
    )
    # The API module declares `requires("cms")`, so register it before mounting.
    app.container.register_instance("cms", cms)
    app.mount_module(portal, prefix="/api")

    async def school_overview(request):
        """Custom Admin page reading straight from the ORM and CMS."""

        return await admin.jinax.render_response(
            "admin_school_overview.html",
            {
                "title": "School overview",
                "student_count": await Student.all().count(),
                "course_count": await Course.all().count(),
                "staff_count": await Staff.all().count(),
                "enrollment_count": await Enrollment.all().count(),
                "news_count": len(
                    [
                        item
                        for item in cms.content_types["news"].items.values()
                        if item.get("status") == "published"
                    ]
                ),
                "admin_url": "/admin/",
                "cms_url": "/admin/cms/",
            },
        )

    admin.add_view(
        school_overview,
        "School overview",
        url="school-overview",
        category="School",
        icon="fa-school",
        permission="admin.view_dashboard",
    )

    @app.get("/")
    @app.get("/<path:spa_path>")
    async def spa(request: Request, spa_path: str = ""):
        return await request.compile(
            "app.html",
            {"school": "Northstar Academy", "admin_url": "/admin/"},
        )

    return app


app = create_app()
