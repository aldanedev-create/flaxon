"""Small JSON repository used by the school example.

Replace this class with a Flaxon database adapter or application repository in
production. The Admin model contract stays the same.
"""

from __future__ import annotations

import json
from asyncio import Lock
from pathlib import Path
from typing import Any


class SchoolRepository:
    """Persist demo collections as JSON while keeping an async API."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._data = self._load()
        if not self._data:
            self._data = {
                "students": [
                    {"id": "1", "name": "Ava Johnson", "grade": "10", "email": "ava@example.test", "active": True},
                    {"id": "2", "name": "Noah Williams", "grade": "11", "email": "noah@example.test", "active": True},
                ],
                "courses": [
                    {"id": "1", "code": "SCI-101", "name": "General Science", "teacher": "Dr. Rivera", "room": "B204"},
                    {"id": "2", "code": "ART-210", "name": "Digital Arts", "teacher": "Ms. Chen", "room": "A108"},
                    {"id": "3", "code": "ENG-305", "name": "Modern Literature", "teacher": "Mr. Patel", "room": "C301"},
                ],
                "staff": [
                    {"id": "1", "name": "Dr. Elena Rivera", "role": "Principal", "email": "erivera@example.test"},
                    {"id": "2", "name": "Marcus Patel", "role": "Counselor", "email": "mpatel@example.test"},
                ],
            }
            self._write()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def _write(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")

    async def list(self, collection: str) -> list[dict[str, Any]]:
        async with self._lock:
            return [dict(item) for item in self._data.get(collection, [])]

    async def get(self, collection: str, object_id: str) -> dict[str, Any] | None:
        records = await self.list(collection)
        return next((item for item in records if str(item.get("id")) == str(object_id)), None)

    async def create(self, collection: str, values: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            records = self._data.setdefault(collection, [])
            numeric_ids = [int(item["id"]) for item in records if str(item.get("id", "")).isdigit()]
            record = {"id": str(max(numeric_ids, default=0) + 1), **values}
            records.append(record)
            self._write()
            return dict(record)

    async def update(self, collection: str, object_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        async with self._lock:
            for record in self._data.get(collection, []):
                if str(record.get("id")) == str(object_id):
                    record.update(values)
                    self._write()
                    return dict(record)
        return None

    async def delete(self, collection: str, object_id: str) -> bool:
        async with self._lock:
            records = self._data.get(collection, [])
            before = len(records)
            self._data[collection] = [item for item in records if str(item.get("id")) != str(object_id)]
            if len(self._data[collection]) == before:
                return False
            self._write()
            return True


repository = SchoolRepository(Path(__file__).resolve().parents[1] / "data" / "school.json")


class Student:
    @classmethod
    async def get_instances(cls):
        return await repository.list("students")

    @classmethod
    async def get_instance(cls, object_id):
        return await repository.get("students", object_id)

    @classmethod
    async def create_instance(cls, data):
        return await repository.create("students", data)

    @classmethod
    async def update_instance(cls, object_id, data):
        return await repository.update("students", object_id, data)

    @classmethod
    async def delete_instance(cls, object_id):
        return await repository.delete("students", object_id)


class Course:
    @classmethod
    async def get_instances(cls):
        return await repository.list("courses")

    @classmethod
    async def get_instance(cls, object_id):
        return await repository.get("courses", object_id)

    @classmethod
    async def create_instance(cls, data):
        return await repository.create("courses", data)

    @classmethod
    async def update_instance(cls, object_id, data):
        return await repository.update("courses", object_id, data)

    @classmethod
    async def delete_instance(cls, object_id):
        return await repository.delete("courses", object_id)


class Staff:
    @classmethod
    async def get_instances(cls):
        return await repository.list("staff")

    @classmethod
    async def get_instance(cls, object_id):
        return await repository.get("staff", object_id)

    @classmethod
    async def create_instance(cls, data):
        return await repository.create("staff", data)

    @classmethod
    async def update_instance(cls, object_id, data):
        return await repository.update("staff", object_id, data)

    @classmethod
    async def delete_instance(cls, object_id):
        return await repository.delete("staff", object_id)
