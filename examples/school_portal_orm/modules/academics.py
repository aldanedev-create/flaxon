"""Course directory module. The catalog now lives in the database."""
from __future__ import annotations

from flaxon.modules import FlaxonModule

from models import Course

academics = FlaxonModule("academics")


def course_payload(course):
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "teacher": course.teacher,
        "room": course.room,
    }


@academics.get("/academics")
async def academics_home(request):
    courses = await Course.all().order_by("code")
    return await request.render("academics.html", {"title": "Academics", "courses": courses})


@academics.get("/academics/courses")
async def courses_page(request):
    courses = await Course.all().order_by("code")
    return await request.render("courses.html", {"title": "Course directory", "courses": courses})


@academics.get("/api/courses")
async def courses_api():
    courses = await Course.all().order_by("code")
    return {"courses": [course_payload(course) for course in courses]}
