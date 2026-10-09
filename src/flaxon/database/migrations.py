from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .manager import DatabaseManager


def _sql_statements(script: str) -> list[str]:
    """Split migration scripts without breaking semicolons in quoted values."""
    statements: list[str] = []
    start = 0
    quote: str | None = None
    index = 0
    while index < len(script):
        char = script[index]
        if quote:
            if char == quote:
                if index + 1 < len(script) and script[index + 1] == quote:
                    index += 2
                    continue
                quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == ";":
            statement = script[start:index].strip()
            if statement:
                statements.append(statement)
            start = index + 1
        index += 1
    statement = script[start:].strip()
    if statement:
        statements.append(statement)
    return statements


@dataclass
class Migration:
    version: str
    name: str
    up: str
    down: str | None = None
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "up": self.up,
            "down": self.down,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Migration:
        return cls(
            version=data["version"],
            name=data["name"],
            up=data["up"],
            down=data.get("down"),
            dependencies=data.get("dependencies", []),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now(),
            applied_at=datetime.fromisoformat(data["applied_at"]) if data.get("applied_at") else None,
        )


class MigrationLoader:
    def __init__(self, migration_dir: str) -> None:
        self.migration_dir = migration_dir

    def load_migrations(self) -> list[Migration]:
        migrations = []

        if not os.path.exists(self.migration_dir):
            os.makedirs(self.migration_dir, exist_ok=True)
            return migrations

        for filename in sorted(os.listdir(self.migration_dir)):
            if not filename.endswith(".json"):
                continue

            path = os.path.join(self.migration_dir, filename)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                migrations.append(Migration.from_dict(data))

        return migrations

    def save_migration(self, migration: Migration) -> None:
        filename = f"{migration.version}_{migration.name}.json"
        path = os.path.join(self.migration_dir, filename)

        os.makedirs(self.migration_dir, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(migration.to_dict(), f, indent=2)


class MigrationRunner:
    def __init__(self, db: DatabaseManager, migration_dir: str, table_name: str = "migrations") -> None:
        self.db = db
        self.loader = MigrationLoader(migration_dir)
        self.table_name = table_name

    async def initialize(self) -> None:
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                version VARCHAR(64) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP NOT NULL,
                down TEXT
            )
        """)

    async def get_applied_versions(self) -> set[str]:
        rows = await self.db.fetch_all(f"SELECT version FROM {self.table_name}")
        return {row["version"] for row in rows}

    async def apply_migration(self, migration: Migration) -> None:
        async with self.db.transaction() as tx:
            for statement in _sql_statements(migration.up):
                await tx.execute(statement)
            await tx.execute(
                f"INSERT INTO {self.table_name} (version, name, applied_at, down) VALUES ($1, $2, $3, $4)",
                migration.version,
                migration.name,
                datetime.now(),
                migration.down or "",
            )

    async def rollback_migration(self, migration: Migration) -> None:
        if migration.down is None:
            raise ValueError(f"Migration {migration.version} has no down script")

        async with self.db.transaction() as tx:
            for statement in _sql_statements(migration.down):
                await tx.execute(statement)
            await tx.execute(
                f"DELETE FROM {self.table_name} WHERE version = $1",
                migration.version,
            )

    async def migrate(self, target_version: str | None = None) -> list[str]:
        await self.initialize()

        applied = await self.get_applied_versions()
        available = self.loader.load_migrations()

        pending = [m for m in available if m.version not in applied]
        pending.sort(key=lambda x: x.version)

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        applied_versions = []

        for migration in pending:
            await self.apply_migration(migration)
            applied_versions.append(migration.version)

        return applied_versions

    async def rollback(self, steps: int = 1) -> list[str]:
        await self.initialize()

        applied = await self.get_applied_versions()
        if not applied:
            return []

        available = {m.version: m for m in self.loader.load_migrations()}

        rolled_back = []
        sorted_applied = sorted(applied)

        for version in reversed(sorted_applied[-steps:]):
            migration = available.get(version)
            if migration is None:
                continue

            await self.rollback_migration(migration)
            rolled_back.append(version)

        return rolled_back

    async def status(self) -> dict[str, Any]:
        await self.initialize()

        applied = await self.get_applied_versions()
        available = self.loader.load_migrations()

        statuses = []
        for migration in available:
            statuses.append({
                "version": migration.version,
                "name": migration.name,
                "applied": migration.version in applied,
                "dependencies": migration.dependencies,
            })

        return {
            "applied_count": len(applied),
            "pending_count": sum(1 for m in available if m.version not in applied),
            "migrations": statuses,
        }

    async def generate_migration(self, name: str, up: str, down: str | None = None) -> str:
        import time

        version = str(int(time.time() * 1000))

        migration = Migration(
            version=version,
            name=name,
            up=up,
            down=down,
        )

        self.loader.save_migration(migration)
        return version
