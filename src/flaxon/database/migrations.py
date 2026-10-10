from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from flaxon.database.sql import statement as sql_statement

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
    """Migration implementation for the database subsystem."""

    version: str
    name: str
    up: str
    down: str | None = None
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
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
        """Construct an instance from its dictionary representation."""
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
    """Migration loader implementation for the database subsystem."""

    def __init__(self, migration_dir: str) -> None:
        self.migration_dir = migration_dir

    def load_migrations(self) -> list[Migration]:
        """Load the migrations."""
        migrations = []

        if not Path(self.migration_dir).exists():
            Path(self.migration_dir).mkdir(parents=True, exist_ok=True)
            return migrations

        for path in sorted(Path(self.migration_dir).iterdir()):
            if path.suffix != ".json":
                continue

            with path.open(encoding="utf-8") as f:
                data = json.load(f)
                migrations.append(Migration.from_dict(data))

        return migrations

    def save_migration(self, migration: Migration) -> None:
        """Save the migration."""
        filename = f"{migration.version}_{migration.name}.json"
        path = str(Path(self.migration_dir) / filename)

        Path(self.migration_dir).mkdir(parents=True, exist_ok=True)

        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(migration.to_dict(), f, indent=2)


class MigrationRunner:
    """Migration runner implementation for the database subsystem."""

    def __init__(self, db: DatabaseManager, migration_dir: str, table_name: str = "migrations") -> None:
        self.db = db
        self.loader = MigrationLoader(migration_dir)
        self.table_name = table_name

    async def initialize(self) -> None:
        """Prepare the configured resources for use."""
        await self.db.execute(
            sql_statement(
                (
                    "\n            CREATE TABLE IF NOT EXISTS {name_0} (\n         "
                    "       version VARCHAR(64) PRIMARY KEY,\n                name"
                    " VARCHAR(255) NOT NULL,\n                applied_at TIMESTAMP"
                    " NOT NULL,\n                down TEXT\n            )\n        "
                ),
                name_0=self.table_name,
            )
        )

    async def get_applied_versions(self) -> set[str]:
        """Return the applied versions."""
        rows = await self.db.fetch_all(sql_statement("SELECT version FROM {name_0}", name_0=self.table_name))
        return {row["version"] for row in rows}

    async def apply_migration(self, migration: Migration) -> None:
        """Apply the migration."""
        async with self.db.transaction() as tx:
            for statement in _sql_statements(migration.up):
                await tx.execute(statement)
            await tx.execute(
                sql_statement(
                    "INSERT INTO {name_0} (version, name, applied_at, down) VALUES ($1, $2, $3, $4)",
                    name_0=self.table_name,
                ),
                migration.version,
                migration.name,
                datetime.now(),
                migration.down or "",
            )

    async def rollback_migration(self, migration: Migration) -> None:
        """Perform the rollback migration operation for migration runner."""
        if migration.down is None:
            raise ValueError(f"Migration {migration.version} has no down script")

        async with self.db.transaction() as tx:
            for statement in _sql_statements(migration.down):
                await tx.execute(statement)
            await tx.execute(
                sql_statement("DELETE FROM {name_0} WHERE version = $1", name_0=self.table_name),
                migration.version,
            )

    async def migrate(self, target_version: str | None = None) -> list[str]:
        """Perform the migrate operation for migration runner."""
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
        """Perform the rollback operation for migration runner."""
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
        """Return the current status."""
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
        """Generate the migration."""
        version = str(int(time.time() * 1000))

        migration = Migration(
            version=version,
            name=name,
            up=up,
            down=down,
        )

        self.loader.save_migration(migration)
        return version
