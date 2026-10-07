"""Project-local administration. Run --help to see available commands."""

import argparse
import asyncio
import getpass

from flaxon.admin.services import AdminAuth, AdminStore
from flaxon.database.adapters.sqlite import SQLiteAdapter
from flaxon.database.manager import DatabaseManager
from flaxon.database.migrations import MigrationRunner
from settings import ROOT, DATA_DIR, DATABASE_PATH


async def migrate(status=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(SQLiteAdapter(database=str(DATABASE_PATH)))
    await db.initialize()
    try:
        runner = MigrationRunner(db, migration_dir=str(ROOT / "migrations"))
        if status:
            report = await runner.status()
            print(f"{report['applied_count']} applied, {report['pending_count']} pending")
        else:
            applied = await runner.migrate()
            print(f"Applied {len(applied)} migration(s).")
    finally:
        await db.close()


def setup_admin(username=None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    store = AdminStore(str(DATABASE_PATH))
    username = (username or input("Administrator username: ")).strip()
    if not username:
        raise ValueError("A username is required")
    if store.get("users", username) is not None:
        raise ValueError("That administrator already exists; use the admin interface to manage it")
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords do not match")
    auth = AdminAuth(users=[], store=store, strict_permissions=True)
    record = auth.add_user(
        {
            "username": username,
            "password": password,
            "roles": ["administrator"],
            "permissions": ["admin.superuser"],
        }
    )

    def create(existing):
        if existing:
            raise ValueError("That administrator already exists")
        existing.update(record)

    store.mutate("users", username, create, default={})
    print(f"Administrator '{username}' created. Sign in at /admin/login.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manage your Flaxon application")
    commands = parser.add_subparsers(dest="command", required=True)
    migration = commands.add_parser("migrate", help="Apply the project's database migrations")
    migration.add_argument("--status", action="store_true")
    admin = commands.add_parser(
        "setup-admin", aliases=["createsuperuser"], help="Create an administrator securely"
    )
    admin.add_argument("--username")
    args = parser.parse_args(argv)
    try:
        if args.command == "migrate":
            asyncio.run(migrate(args.status))
        else:
            setup_admin(args.username)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
