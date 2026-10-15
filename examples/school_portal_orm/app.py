"""Northstar Academy on the ORM: same portal as examples/school_portal, but the
models are flaxon.db (Tortoise) models instead of hand-written JSON classes.

Run from this directory:

    python management.py migrate
    python management.py setup-admin
    python seed.py
    python management.py runserver
"""
from __future__ import annotations

from flaxon import Flaxon
from flaxon.admin.cms import CMSField, ContentType
from flaxon.db.admin import configure_admin
from flaxon.jinax import Jinax
from flaxon.jinax.loaders import CompositeLoader, FileSystemLoader

from models import Course, Staff, Student
from modules.academics import academics
from modules.community import community
from modules.website import website

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

    # Management mode only needs settings, models and migrations: it skips
    # templates, Admin and CMS so commands never open the AdminStore.
    if app.is_management:
        return app

    app.mount_static("/school-static", str(settings.root / "static"))
    app.use_templates(Jinax(str(settings.root / "templates"), auto_reload=settings.DEBUG))

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
    # Modules declare `requires("cms")`, so register it before mounting them.
    app.container.register_instance("cms", cms)
    app.mount_module(website, prefix="")
    app.mount_module(academics, prefix="")
    app.mount_module(community, prefix="")

    async def school_overview(request):
        """Custom Admin page reading straight from the ORM."""

        return await admin.jinax.render_response(
            "admin_school_overview.html",
            {
                "title": "School overview",
                "student_count": await Student.all().count(),
                "course_count": await Course.all().count(),
                "staff_count": await Staff.all().count(),
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
    return app


app = create_app()
