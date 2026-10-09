from __future__ import annotations

import argparse
from typing import Any

from ..base import Command


class MigrateCommand(Command):
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
            from flaxon.database.adapters.sqlite import SQLiteAdapter

            return SQLiteAdapter(database=database)

        from urllib.parse import urlsplit

        parts = urlsplit(database)
        scheme = (parts.scheme or "").split("+")[0]

        if scheme in {"postgres", "postgresql"}:
            from flaxon.database.adapters.postgresql import PostgreSQLAdapter

            return PostgreSQLAdapter(
                host=parts.hostname or "localhost",
                port=parts.port or 5432,
                database=parts.path.lstrip("/") or "postgres",
                user=parts.username or "postgres",
                password=parts.password or "",
            )
        if scheme == "mysql":
            from flaxon.database.adapters.mysql import MySQLAdapter

            return MySQLAdapter(
                host=parts.hostname or "localhost",
                port=parts.port or 3306,
                database=parts.path.lstrip("/") or "",
                user=parts.username or "root",
                password=parts.password or "",
            )
        if scheme == "sqlite":
            from flaxon.database.adapters.sqlite import SQLiteAdapter

            return SQLiteAdapter(database=parts.path.lstrip("/") or ":memory:")

        raise ValueError(f"Unsupported database scheme: '{scheme}'. Use sqlite, postgresql, or mysql.")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        import asyncio

        from flaxon.database.manager import DatabaseManager
        from flaxon.database.migrations import MigrationRunner

        try:
            adapter = self._build_adapter(args.database)
        except ValueError as exc:
            console.error(str(exc))
            return 1

        db = DatabaseManager(adapter)
        runner = MigrationRunner(db, migration_dir=args.migrations_dir)

        async def main() -> int:
            await db.initialize()
            try:
                if args.status:
                    status = await runner.status()
                    console.info(f"{status['applied_count']} applied, {status['pending_count']} pending")
                    for m in status["migrations"]:
                        mark = "[x]" if m["applied"] else "[ ]"
                        console.info(f"  {mark} {m['version']}  {m['name']}")
                    return 0

                if args.direction == "up":
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

                # direction == "down"
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
            finally:
                await db.close()

        try:
            return asyncio.run(main())
        except Exception as exc:
            console.error(f"Migration failed: {exc}")
            return 1
