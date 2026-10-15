"""Root project models. Run `python management.py makemigrations` after editing.

These are Tortoise models through flaxon.db, so Admin gets create/update/delete
hooks automatically — no hand-written repository contract required.
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
