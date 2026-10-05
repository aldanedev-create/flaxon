"""Course directory module."""

from __future__ import annotations

from flaxon.modules import FlaxonModule

academics = FlaxonModule("academics")
academics.requires("school")


@academics.get("/academics")
async def academics_home(request, school):
    courses = await school.list("courses")
    return await request.render("academics.html", {"title": "Academics", "courses": courses})


@academics.get("/academics/courses")
async def courses_page(request, school):
    courses = await school.list("courses")
    return await request.render("courses.html", {"title": "Course directory", "courses": courses})


@academics.get("/api/courses")
async def courses_api(school):
    return {"courses": await school.list("courses")}
