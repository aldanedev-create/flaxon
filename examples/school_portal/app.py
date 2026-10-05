"""Northstar Academy: Admin, CMS, Jinax, and Flaxon modules in one app.

Run from the repository root:

    flaxon run examples.school_portal.app:app --reload --port 8000

Demo Admin login: admin / School123!
Change the password with FLAXON_SCHOOL_ADMIN_PASSWORD before deployment.
"""

from __future__ import annotations

import os
from pathlib import Path

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.cms import CMS, CMSField, ContentType
from flaxon.jinax import Jinax
from flaxon.jinax.loaders import CompositeLoader, FileSystemLoader

from .modules.academics import academics
from .modules.community import community
from .modules.repository import Course, Staff, Student, repository
from .modules.website import website

ROOT = Path(__file__).parent
DATA = ROOT / "data"

app = Flaxon("northstar-academy", debug=True)
app.use_templates(Jinax(ROOT / "templates", auto_reload=True, strict_undefined=True))
app.mount_static("/school-static", str(ROOT / "static"))

admin = AdminDashboard(
    app,
    url_prefix="/admin",
    config=AdminConfig(
        site_title="Northstar Academy",
        site_header="Northstar Academy Admin",
        index_title="School operations",
        timezone="UTC",
        settings={"environment": "development", "public_site": "http://127.0.0.1:8000"},
    ),
    storage_path=str(DATA / "admin.sqlite3"),
    upload_dir=str(DATA / "uploads"),
    users=[
        {
            "username": "admin",
            "password": os.getenv("FLAXON_SCHOOL_ADMIN_PASSWORD", "School123!"),
            "email": "admin@northstar.example",
            "roles": ["administrator"],
        }
    ],
)
admin.jinax.environment.loader = CompositeLoader(
    [FileSystemLoader(ROOT / "templates"), admin.jinax.environment.loader]
)

admin.register(
    Student,
    name="student",
    list_display=["id", "name", "grade", "email", "active"],
    search_fields=["name", "email", "grade"],
    list_filter=["grade", "active"],
    fields=["name", "grade", "email", "active"],
)
admin.register(
    Course,
    name="course",
    list_display=["id", "code", "name", "teacher", "room"],
    search_fields=["code", "name", "teacher"],
    list_filter=["room"],
    fields=["code", "name", "teacher", "room"],
)
admin.register(
    Staff,
    name="staff",
    list_display=["id", "name", "role", "email"],
    search_fields=["name", "role", "email"],
    list_filter=["role"],
    fields=["name", "role", "email"],
)

cms = CMS(app, url_prefix="/admin/cms", title="Northstar Content", auth=admin.auth)
cms.register(
    ContentType(
        name="news",
        label="News item",
        label_plural="News",
        fields=[
            CMSField("title", "Title", required=True),
            CMSField("summary", "Summary", required=True),
            CMSField("category", "Category", type="select", choices=["Community", "Academics", "Arts & culture", "Athletics"], required=True),
            CMSField("body", "Body", type="richtext"),
            CMSField("status", "Status", type="select", choices=["draft", "published", "archived"]),
        ],
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
        fields=[
            CMSField("title", "Title", required=True),
            CMSField("date", "Date", type="date", required=True),
            CMSField("time", "Time", type="text"),
            CMSField("location", "Location", type="text", required=True),
            CMSField("category", "Category", type="select", choices=["Community", "Academics", "Arts & culture", "Athletics"], required=True),
            CMSField("description", "Description", type="textarea"),
            CMSField("status", "Status", type="select", choices=["draft", "published", "archived"]),
        ],
        list_display=["title", "date", "location", "status"],
        list_filter=["status", "category"],
        search_fields=["title", "location", "description"],
    )
)

news = cms.content_types["news"]
if not news.items:
    news.create(
        {
            "title": "Welcome to Northstar",
            "summary": "A new semester of curiosity, community, and discovery.",
            "category": "Community",
            "body": "<p>Families can follow campus updates here throughout the school year.</p>",
            "status": "published",
        }
    )
    cms._save(news)

events = cms.content_types["events"]
if not events.items:
    for event in (
        {
            "title": "Family welcome evening",
            "date": "2026-10-15",
            "time": "5:00 PM",
            "location": "School auditorium",
            "category": "Community",
            "description": "Meet teachers, tour the studios, and start the year together.",
            "status": "published",
        },
        {
            "title": "Career and pathways fair",
            "date": "2026-10-22",
            "time": "10:00 AM",
            "location": "Main hall",
            "category": "Academics",
            "description": "Professionals and alumni share the many ways students can build their future.",
            "status": "published",
        },
        {
            "title": "Inter-house debate finals",
            "date": "2026-10-30",
            "time": "6:30 PM",
            "location": "Forum theatre",
            "category": "Arts & culture",
            "description": "Our student houses meet for an evening of research, argument, and good spirit.",
            "status": "published",
        },
    ):
        events.create(event)
    cms._save(events)

app.container.register_instance("school", repository)
app.container.register_instance("cms", cms)
app.mount_module(website, prefix="")
app.mount_module(academics, prefix="")
app.mount_module(community, prefix="")


async def school_overview(request):
    """Custom Admin page showing the module-backed school summary."""

    students = await repository.list("students")
    courses = await repository.list("courses")
    staff = await repository.list("staff")
    news = [item for item in cms.content_types["news"].items.values() if item.get("status") == "published"]
    return await admin.jinax.render_response(
        "admin_school_overview.html",
        {
            "title": "School overview",
            "student_count": len(students),
            "course_count": len(courses),
            "staff_count": len(staff),
            "news_count": len(news),
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.school_portal.app:app", host="127.0.0.1", port=8000, reload=True)
