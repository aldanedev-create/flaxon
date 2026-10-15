"""Public JSON API backing the Teloce interface.

Everything here reads the same flaxon.db (Tortoise) rows and CMS content that the
Admin uses, so an enrollment created in the browser shows up in Admin and vice
versa. Mounted at `/api` by app.py.
"""
from __future__ import annotations

from datetime import datetime

from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule
from flaxon.validation import Schema, fields

from models import Course, Enrollment, Staff, Student

portal = FlaxonModule("portal")
portal.requires("cms")


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
    for item in sorted(items, key=lambda value: str(value.get("date", ""))):
        record = dict(item)
        try:
            date = datetime.strptime(str(record.get("date", "")), "%Y-%m-%d")
            record["day"] = date.strftime("%d")
            record["month"] = date.strftime("%b").upper()
            record["date_label"] = date.strftime("%b %d, %Y")
        except ValueError:
            record["day"] = "--"
            record["month"] = "DATE"
            record["date_label"] = record.get("date") or "Date to be announced"
        formatted.append(record)
    return formatted


def student_record(student: Student) -> dict:
    return {
        "id": student.id,
        "name": student.name,
        "grade": student.grade,
        "email": student.email,
        "active": student.active,
    }


def course_record(course: Course) -> dict:
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "teacher": course.teacher,
        "room": course.room,
    }


def enrollment_record(enrollment: Enrollment) -> dict:
    return {
        "id": enrollment.id,
        "student_id": enrollment.student_id,
        "course_id": enrollment.course_id,
        "grade": enrollment.grade,
        "enrolled_on": str(enrollment.enrolled_on) if enrollment.enrolled_on else None,
    }


@portal.get("/overview")
async def overview(request, cms):
    return {
        "school": "Northstar Academy",
        "students": await Student.all().count(),
        "courses": await Course.all().count(),
        "staff": await Staff.all().count(),
        "enrollments": await Enrollment.all().count(),
        "news": len(published_news(cms)),
        "events": len(published_events(cms)),
    }


@portal.get("/students")
async def students(request):
    rows = await Student.all().order_by("name")
    return {"items": [student_record(s) for s in rows]}


@portal.get("/courses")
async def courses(request):
    rows = await Course.all().order_by("code")
    return {"items": [course_record(c) for c in rows]}


@portal.get("/enrollments")
async def enrollments(request):
    rows = await Enrollment.all().order_by("student_id", "course_id")
    return {"items": [enrollment_record(e) for e in rows]}


@portal.get("/news")
async def news(request, cms):
    return {"items": published_news(cms)}


@portal.get("/events")
async def events(request, cms):
    return {"items": published_events(cms)}


class EnrollSchema(Schema):
    student_id = fields.IntField(required=True)
    course_id = fields.IntField(required=True)
    grade = fields.StrField(required=False, max_length=5)


@portal.post("/enrollments")
async def create_enrollment(data: EnrollSchema):
    payload = data.to_dict()
    student_id = payload["student_id"]
    course_id = payload["course_id"]
    if not await Student.filter(id=student_id).exists():
        return JSONResponse({"error": "Unknown student."}, status_code=422)
    if not await Course.filter(id=course_id).exists():
        return JSONResponse({"error": "Unknown course."}, status_code=422)
    already = await Enrollment.filter(student_id=student_id, course_id=course_id).exists()
    if already:
        return JSONResponse({"error": "Already enrolled."}, status_code=409)
    enrollment = await Enrollment.create(
        student_id=student_id,
        course_id=course_id,
        grade=payload.get("grade"),
    )
    return JSONResponse(enrollment_record(enrollment), status_code=201)
