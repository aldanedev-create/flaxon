"""Public school website module."""

from __future__ import annotations

from datetime import datetime

from flaxon.modules import FlaxonModule

website = FlaxonModule("website")
website.requires("school")
website.requires("cms")


def published_news(cms):
    content_type = cms.content_types.get("news")
    if content_type is None:
        return []
    items = [item for item in content_type.items.values() if item.get("status") == "published"]
    return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)


def published_events(cms):
    content_type = cms.content_types.get("events")
    if content_type is None:
        return []
    items = [item for item in content_type.items.values() if item.get("status") == "published"]
    formatted = []
    for item in sorted(items, key=lambda value: value.get("date", "")):
        record = dict(item)
        try:
            date = datetime.strptime(str(record.get("date", "")), "%Y-%m-%d")
            record["date_label"] = date.strftime("%b %d, %Y").replace(" 0", " ")
            record["day"] = date.strftime("%d")
            record["month"] = date.strftime("%b").upper()
        except ValueError:
            record["date_label"] = record.get("date") or "Date to be announced"
            record["day"] = "--"
            record["month"] = "DATE"
        formatted.append(record)
    return formatted


@website.get("/")
async def home(request, school, cms):
    courses = await school.list("courses")
    staff = await school.list("staff")
    return await request.render(
        "home.html",
        {
            "title": "Northstar Academy",
            "course_count": len(courses),
            "staff_count": len(staff),
            "news": published_news(cms)[:2],
            "events": published_events(cms)[:3],
            "admin_url": "/admin/login",
            "cms_url": "/admin/cms/",
        },
    )


@website.get("/about")
async def about(request, school):
    staff = await school.list("staff")
    return await request.render("about.html", {"title": "About Northstar", "staff": staff})


@website.get("/students")
async def student_life(request):
    return await request.render("student_life.html", {"title": "Student life"})


@website.get("/admissions")
async def admissions(request):
    return await request.render("admissions.html", {"title": "Admissions"})


@website.get("/contact")
async def contact(request):
    return await request.render("contact.html", {"title": "Contact Northstar"})


@website.get("/calendar")
async def calendar(request, cms):
    return await request.render("calendar.html", {"title": "School calendar", "events": published_events(cms)})
