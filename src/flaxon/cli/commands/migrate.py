from __future__ import annotations

import argparse
import asyncio
from typing import Any
from urllib.parse import urlsplit

from flaxon._imports import import_attribute
from flaxon.cli.base import Command


class MigrateCommand(Command):
    """Migrate command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="migrate",
            handler=self._run,
            help_text="Run database migrations",
            description="Apply or rollback database migrations",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--database",
            default="flaxon.db",
            help=(
                "Database to migrate. A bare path is treated as a SQLite "
                "file (default: flaxon.db). Also accepts postgresql://... "
                "or mysql://... URLs."
            ),
        )
        parser.add_argument(
            "--migrations-dir", default="migrations", help="Directory containing migration files"
        )
        parser.add_argument("--direction", choices=["up", "down"], default="up", help="Migration direction")
        parser.add_argument("--target", help="For --direction up: only apply migrations up to this version")
        parser.add_argument(
            "--steps", type=int, default=1, help="For --direction down: number of migrations to roll back"
        )
        parser.add_argument("--status", action="store_true", help="Show migration status and exit")
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be applied without applying it"
        )

    def _build_adapter(self, database: str) -> Any:
        if "://" not in database:
            sqlite_adapter_type = import_attribute("flaxon.database.adapters.sqlite", "SQLiteAdapter")

            return sqlite_adapter_type(database=database)

        parts = urlsplit(database)
        scheme = (parts.scheme or "").split("+")[0]

        if scheme in {"postgres", "postgresql"}:
            postgre_sqladapter_type = import_attribute(
                "flaxon.database.adapters.postgresql", "PostgreSQLAdapter"
            )

            return postgre_sqladapter_type(
                host=parts.hostname or "localhost",
                port=parts.port or 5432,
                database=parts.path.lstrip("/") or "postgres",
                user=parts.username or "postgres",
                password=parts.password or "",
            )
        if scheme == "mysql":
            my_sqladapter_type = import_attribute("flaxon.database.adapters.mysql", "MySQLAdapter")

            return my_sqladapter_type(
                host=parts.hostname or "localhost",
                port=parts.port or 3306,
                database=parts.path.lstrip("/") or "",
                user=parts.username or "root",
                password=parts.password or "",
            )
        if scheme == "sqlite":
            sqlite_adapter_type = import_attribute("flaxon.database.adapters.sqlite", "SQLiteAdapter")

            return sqlite_adapter_type(database=parts.path.lstrip("/") or ":memory:")

        raise ValueError(f"Unsupported database scheme: '{scheme}'. Use sqlite, postgresql, or mysql.")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        database_manager_type = import_attribute("flaxon.database.manager", "DatabaseManager")
        migration_runner_type = import_attribute("flaxon.database.migrations", "MigrationRunner")

        try:
            adapter = self._build_adapter(args.database)
        except ValueError as exc:
            console.error(str(exc))
            return 1

        db = database_manager_type(adapter)
        runner = migration_runner_type(db, migration_dir=args.migrations_dir)

        try:
            return asyncio.run(self._execute_migrations(args, console, db, runner))
        except Exception as exc:
            console.error(f"Migration failed: {exc}")
            return 1

    async def _execute_migrations(self, args, console, db, runner):
        await db.initialize()
        try:
            if args.status:
                return await self._show_status(console, runner)
            if args.direction == "up":
                return await self._migrate_up(args, console, runner)
            return await self._migrate_down(args, console, runner)
        finally:
            await db.close()

    @staticmethod
    async def _show_status(console, runner):
        status = await runner.status()
        console.info(f"{status['applied_count']} applied, {status['pending_count']} pending")
        for m in status["migrations"]:
            mark = "[x]" if m["applied"] else "[ ]"
            console.info(f"  {mark} {m['version']}  {m['name']}")
        return 0

    @staticmethod
    async def _migrate_up(args, console, runner):
        status = await runner.status()
        pending = [m for m in status["migrations"] if not m["applied"]]
        if args.target:
            pending = [m for m in pending if m["version"] <= args.target]

        if not pending:
            console.info("No pending migrations.")
            return 0

        if args.dry_run:
            console.info(f"Would apply {len(pending)} migration(s):")
            for m in pending:
                console.info(f"  {m['version']}  {m['name']}")
            return 0

        console.info(f"Applying {len(pending)} migration(s)...")
        applied = await runner.migrate(target_version=args.target)
        for version in applied:
            console.success(f"  [x] {version}")
        console.success(f"Applied {len(applied)} migration(s).")
        return 0

    @staticmethod
    async def _migrate_down(args, console, runner):
        console.warning("This will rollback migrations!")

        if args.dry_run:
            status = await runner.status()
            applied_versions = sorted(m["version"] for m in status["migrations"] if m["applied"])
            to_roll_back = applied_versions[-args.steps :] if applied_versions else []
            if not to_roll_back:
                console.info("Nothing to roll back.")
                return 0
            console.info(f"Would roll back {len(to_roll_back)} migration(s):")
            for version in reversed(to_roll_back):
                console.info(f"  {version}")
            return 0

        rolled_back = await runner.rollback(steps=args.steps)
        if not rolled_back:
            console.info("Nothing to roll back.")
            return 0
        for version in rolled_back:
            console.success(f"  [ ] {version}")
        console.success(f"Rolled back {len(rolled_back)} migration(s).")
        return 0
