"""Only explicitly registered models appear in Admin.

No create_instance/update_instance boilerplate here: these are flaxon.db models,
so the registry wraps them with the ORM adapter and derives forms, filters and
search from the field definitions.
"""
from models import Course, Staff, Student


def register(admin):
    admin.register(
        Student,
        list_display=["id", "name", "grade", "email", "active"],
        search_fields=["name", "email", "grade"],
        list_filter=["grade", "active"],
        fields=["name", "grade", "email", "active"],
        ordering=["name"],
    )
    admin.register(
        Course,
        list_display=["id", "code", "name", "teacher", "room"],
        search_fields=["code", "name", "teacher"],
        list_filter=["room"],
        fields=["code", "name", "teacher", "room"],
        ordering=["code"],
    )
    admin.register(
        Staff,
        list_display=["id", "name", "role", "email"],
        search_fields=["name", "role", "email"],
        list_filter=["role"],
        fields=["name", "role", "email"],
        ordering=["name"],
    )
