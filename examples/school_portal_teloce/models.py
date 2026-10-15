"""Root project models. Run `python management.py makemigrations` after editing.

These are Tortoise models through flaxon.db, so Admin gets create/update/delete
hooks automatically and modules can query them with the async ORM. The Teloce
interface in `ui/` reads the same rows through the JSON API in `modules/portal.py`.
"""
from flaxon.db import Model, fields


class Student(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120)
    grade = fields.CharField(max_length=10)
    email = fields.CharField(max_length=255)
    active = fields.BooleanField(default=True)

    class Meta:
        table = "school_students"

    def __str__(self):
        return self.name


class Course(Model):
    id = fields.IntField(primary_key=True)
    code = fields.CharField(max_length=20, unique=True)
    name = fields.CharField(max_length=120)
    teacher = fields.CharField(max_length=120)
    room = fields.CharField(max_length=20)

    class Meta:
        table = "school_courses"

    def __str__(self):
        return f"{self.code} — {self.name}"


class Staff(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120)
    role = fields.CharField(max_length=80)
    email = fields.CharField(max_length=255)

    class Meta:
        table = "school_staff"

    def __str__(self):
        return self.name


class Enrollment(Model):
    """A student enrolled in a course. Demonstrates a Tortoise foreign key and a
    write path that the Teloce UI uses directly (POST /api/enrollments)."""

    id = fields.IntField(primary_key=True)
    student = fields.ForeignKeyField("models.Student", related_name="enrollments")
    course = fields.ForeignKeyField("models.Course", related_name="course_enrollments")
    grade = fields.CharField(max_length=5, null=True)
    enrolled_on = fields.DateField(null=True)

    class Meta:
        table = "school_enrollments"

    def __str__(self):
        return f"{self.student_id} → {self.course_id}"
