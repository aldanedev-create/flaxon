"""Load the demo catalogue and CMS content once, after `management.py migrate`.

Run with:

    python seed.py

Safe to re-run: rows that already exist are left alone.
"""
from __future__ import annotations

import asyncio

from app import create_app
from models import Course, Staff, Student

COURSES = [
    ("SCI-101", "General Science", "Dr. Rivera", "B204"),
    ("ART-210", "Digital Arts", "Ms. Chen", "A108"),
    ("ENG-305", "Modern Literature", "Mr. Patel", "C301"),
]

STAFF = [
    ("Dr. Elena Rivera", "Principal", "erivera@example.test"),
    ("Marcus Patel", "Counselor", "mpatel@example.test"),
]

STUDENTS = [
    ("Ava Johnson", "10", "ava@example.test"),
    ("Noah Williams", "11", "noah@example.test"),
]

NEWS = [
    {
        "title": "Welcome to Northstar",
        "summary": "A new semester of curiosity, community, and discovery.",
        "category": "Community",
        "body": "<p>Families can follow campus updates here throughout the school year.</p>",
        "status": "published",
    }
]

EVENTS = [
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
]


async def seed_orm():
    created = 0
    for code, name, teacher, room in COURSES:
        if not await Course.filter(code=code).exists():
            await Course.create(code=code, name=name, teacher=teacher, room=room)
            created += 1
    for name, role, email in STAFF:
        if not await Staff.filter(email=email).exists():
            await Staff.create(name=name, role=role, email=email)
            created += 1
    for name, grade, email in STUDENTS:
        if not await Student.filter(email=email).exists():
            await Student.create(name=name, grade=grade, email=email, active=True)
            created += 1
    return created


def seed_cms(app):
    cms = getattr(app, "cms", None)
    if cms is None:
        return 0
    written = 0
    for name, payloads in (("news", NEWS), ("events", EVENTS)):
        content_type = cms.content_types.get(name)
        if content_type is None:
            continue
        existing = {item.get("title") for item in content_type.items.values()}
        for payload in payloads:
            if payload["title"] in existing:
                continue
            content_type.create(payload)
            written += 1
        if written:
            cms._save(content_type)
    return written


async def main():
    app = create_app()
    async with app.db:
        created = await seed_orm()
    written = seed_cms(app)
    print(f"ORM rows created: {created}")
    print(f"CMS items created: {written}")


if __name__ == "__main__":
    asyncio.run(main())
