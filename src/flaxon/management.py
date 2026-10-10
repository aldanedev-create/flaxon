"""Project management commands using the same settings and mounted modules as the server."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import importlib
import os
import sys
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute, import_module
from flaxon.config import Settings, management_mode

TORTOISE_ORM: dict[str, Any] = {}


def load_application(application: str):
    """Load the application."""
    module_name, attribute = application.split(":", 1)
    token = management_mode.set(True)
    try:
        app = getattr(importlib.import_module(module_name), attribute)
    finally:
        management_mode.reset(token)
    if not hasattr(app, "db") or not hasattr(app.db, "configuration"):
        raise ValueError("Use Flaxon.from_settings() in app.py for ORM management commands")
    return app


def admin_store(settings):
    """Perform the admin store operation for this subsystem."""
    if getattr(settings, "ADMIN_STORE_BACKEND", "sqlite") == "orm":
        ormadmin_store_type = import_attribute("flaxon.db.admin_store", "ORMAdminStore")

        return ormadmin_store_type(settings.DATABASE_URL)
    admin_store_type = import_attribute("flaxon.admin.services", "AdminStore")

    path = Path(settings.ADMIN_STORAGE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return admin_store_type(str(path))


def setup_admin(settings, username=None):
    """Perform the setup admin operation for this subsystem."""
    admin_auth_type = import_attribute("flaxon.admin.services", "AdminAuth")

    store = admin_store(settings)
    username = (username or input("Administrator username: ")).strip()
    if not username:
        raise ValueError("A username is required")
    if store.get("users", username) is not None:
        raise ValueError("That administrator already exists")
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords do not match")
    auth = admin_auth_type(users=[], store=store, strict_permissions=True)
    record = auth.add_user({
        "username": username,
        "password": password,
        "roles": ["administrator"],
        "permissions": ["admin.superuser"],
    })

    def create(existing):
        if existing:
            raise ValueError("That administrator already exists")
        existing.update(record)

    store.mutate("users", username, create, default={})
    print(f"Administrator '{username}' created. Sign in at /admin/login.")


def _project_command_parser():
    parser = argparse.ArgumentParser(description="Manage your Flaxon project")
    commands = parser.add_subparsers(dest="command", required=True)
    copy_store = commands.add_parser(
        "migrate-admin-store", help="Copy a legacy SQLite Admin store into an empty migrated ORM store"
    )
    copy_store.add_argument("source")
    commands.add_parser("check", help="Validate settings, model discovery, and Admin registration")
    make = commands.add_parser("makemigrations", help="Generate Python migrations from models")
    make.add_argument("labels", nargs="*")
    make.add_argument("--name")
    make.add_argument("--empty", action="store_true")
    migration = commands.add_parser("migrate", help="Apply migrations, or show their status / plan")
    migration.add_argument("targets", nargs="*")
    migration.add_argument("--status", action="store_true")
    migration.add_argument("--plan", action="store_true")
    sql = commands.add_parser("sqlmigrate", help="Preview migration SQL")
    sql.add_argument("label")
    sql.add_argument("migration")
    sql.add_argument("--backward", action="store_true")
    commands.add_parser("shell", help="Open an ORM-aware interactive shell (install IPython)")
    admin = commands.add_parser("setup-admin", aliases=["createsuperuser"])
    admin.add_argument("--username")
    server = commands.add_parser("runserver", help="Run the development server")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8000)
    server.add_argument("--no-reload", action="store_true")
    return parser


def _orm_command_arguments(args):
    cli = ["-c", "flaxon.management.TORTOISE_ORM"]
    if args.command == "makemigrations":
        cli += ["makemigrations", *args.labels]
        if args.name:
            cli += ["--name", args.name]
        if args.empty:
            cli += ["--empty"]
    elif args.command == "migrate":
        cli += ["history" if args.status else "migrate", *args.targets]
        if args.plan and not args.status:
            cli += ["--dry-run"]
    elif args.command == "sqlmigrate":
        cli += ["sqlmigrate", args.label, args.migration]
        if args.backward:
            cli += ["--backward"]
    else:
        cli += ["shell"]
    return cli


def _prepare_project_root(project_root):
    if project_root is not None:
        root = Path(project_root).resolve()
        os.chdir(root)
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))


def execute(argv=None, *, settings="settings", application="app:app", project_root=None):
    """Run project commands; the generated management.py only calls this function."""
    _prepare_project_root(project_root)
    parser = _project_command_parser()
    # Preserve existing module command parsing and argument handling.
    args_list = list(sys.argv[1:] if argv is None else argv)
    known = {
        "check",
        "makemigrations",
        "migrate",
        "sqlmigrate",
        "shell",
        "setup-admin",
        "createsuperuser",
        "runserver",
        "migrate-admin-store",
        "-h",
        "--help",
    }
    if args_list and args_list[0] not in known:
        console_type = import_attribute("flaxon.cli.console", "Console")
        create_parser = import_attribute("flaxon.cli.main", "create_parser")

        custom_args = create_parser().parse_args(args_list)
        command = custom_args._commands[custom_args.command]
        return command.run(custom_args, console_type())
    args = parser.parse_args(args_list)
    try:
        project_settings = Settings(settings)
        if args.command == "migrate-admin-store":
            if getattr(project_settings, "ADMIN_STORE_BACKEND", "sqlite") != "orm":
                raise ValueError("Set ADMIN_STORE_BACKEND = 'orm' first")
            store = admin_store(project_settings)
            try:
                print(store.import_sqlite(args.source))
            finally:
                store.close()
            return 0
        if args.command in {"setup-admin", "createsuperuser"}:
            setup_admin(project_settings, args.username)
            return 0
        if args.command == "runserver":
            uvicorn = import_module("uvicorn")

            uvicorn.run(application, host=args.host, port=args.port, reload=not args.no_reload)
            return 0
        app = load_application(application)
        TORTOISE_ORM.clear()
        TORTOISE_ORM.update(app.db.configuration())
        if args.command == "check":
            tortoise_context_type = import_attribute("tortoise.context", "TortoiseContext")

            async def check():
                async with tortoise_context_type() as context:
                    await context.init(config=TORTOISE_ORM, init_connections=False)

            asyncio.run(check())
            registry_type = import_attribute("flaxon.admin.registry", "Registry")
            register_project_models = import_attribute("flaxon.db.admin", "register_project_models")

            register_project_models(app, registry_type())
            print("Settings, models, and Admin registrations passed. No database schema was changed.")
            return 0
        project_settings.prepare_database_directory()
        run_cli_async = import_attribute("tortoise.cli.cli", "run_cli_async")

        cli = _orm_command_arguments(args)
        return asyncio.run(run_cli_async(cli))
    except (ValueError, OSError, ImportError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
