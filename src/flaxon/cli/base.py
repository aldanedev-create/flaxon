from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute, import_module


class Command:
    """Command implementation for the cli subsystem."""

    def __init__(
        self,
        name: str,
        handler: Callable,
        help_text: str = "",
        description: str = "",
    ) -> None:
        self.name = name
        self.handler = handler
        self.help_text = help_text
        self.description = description

    def add_parser(self, subparsers: Any) -> None:
        """Add the parser."""
        parser = subparsers.add_parser(self.name, help=self.help_text, description=self.description)
        parser.set_defaults(func=self.handler)
        self._add_arguments(parser)

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Perform the  add arguments operation for command."""
        pass

    def run(self, args: argparse.Namespace, console: Any) -> int:
        """Run the configured operation."""
        return self.handler(args, console)


class CommandGroup:
    """Command group implementation for the cli subsystem."""

    def __init__(self, name: str, help_text: str = "") -> None:
        self.name = name
        self.help_text = help_text
        self.commands: list[Command] = []

    def add(self, command: Command) -> None:
        """Add the supplied item to this collection."""
        self.commands.append(command)

    def add_parser(self, subparsers: Any) -> None:
        """Add the parser."""
        for command in self.commands:
            command.add_parser(subparsers)


class RunCommand(Command):
    """Run command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="run",
            handler=self._run,
            help_text="Run a Flaxon ASGI application",
            description="Run a Flaxon application using Uvicorn",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
        parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
        parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
        parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        try:
            uvicorn = import_module("uvicorn")
        except ImportError:
            console.error("Uvicorn is not installed. Run: pip install uvicorn")
            return 1

        console.info(f"Starting Flaxon application: {args.application}")
        console.info(f"Host: {args.host}, Port: {args.port}")

        if args.reload or args.workers > 1:
            uvicorn.run(
                args.application,
                host=args.host,
                port=args.port,
                reload=args.reload,
                workers=args.workers,
            )
        else:
            import_string = import_attribute("flaxon.utils.import_string", "import_string")

            app = import_string(args.application)
            uvicorn.run(app, host=args.host, port=args.port)

        return 0


class RoutesCommand(Command):
    """Routes command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="routes",
            handler=self._routes,
            help_text="List registered HTTP and WebSocket routes",
            description="Display all registered routes in the application",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")

    def _routes(self, args: argparse.Namespace, console: Any) -> int:
        import_string = import_attribute("flaxon.utils.import_string", "import_string")

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        console.info(f"Routes for {app.name}")

        table_data = []

        for route in app.router.routes:
            methods = ",".join(sorted(route.methods))
            table_data.append([methods, route.path, route.name or ""])

        for route in app.router.websocket_routes:
            table_data.append(["WEBSOCKET", route.path, route.name or ""])

        if table_data:
            console.table(["Method", "Path", "Name"], table_data)
        else:
            console.info("No routes registered")

        return 0


class DoctorCommand(Command):
    """Doctor command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="doctor",
            handler=self._doctor,
            help_text="Check application configuration and routes",
            description="Run diagnostics on the application",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")

    def _doctor(self, args: argparse.Namespace, console: Any) -> int:
        import_string = import_attribute("flaxon.utils.import_string", "import_string")

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        warnings = []
        failures = []

        console.info(f"Flaxon Doctor - {app.name}")

        console.success("[PASS] Application imported successfully")
        console.success(f"[PASS] {len(app.router.routes)} HTTP route(s) registered")
        console.success(f"[PASS] {len(app.router.websocket_routes)} WebSocket route(s) registered")

        if app.debug and str(app.config.get("ENV", "development")).lower() == "production":
            warnings.append("Debug mode is enabled in production.")

        if app.config.get("SECRET_KEY") in {None, "", "change-me", "change-this-in-production"}:
            warnings.append("A strong production SECRET_KEY is not configured.")

        seen = set()
        for route in app.router.routes:
            key = (route.path, tuple(sorted(route.methods)))
            if key in seen:
                failures.append(f"Duplicate route: {route.methods} {route.path}")
            seen.add(key)

        for warning in warnings:
            console.warning(f"[WARN] {warning}")

        for failure in failures:
            console.error(f"[FAIL] {failure}")

        console.info(f"Result: {len(warnings)} warning(s), {len(failures)} failure(s)")

        return 1 if failures else 0


class NewCommand(Command):
    """New command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="new",
            handler=self._new,
            help_text="Create a new Flaxon project",
            description="Generate a starter Flaxon project",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", help="Project directory name")
        parser.add_argument("--template", default="basic", help="Project template to use")

    def _new(self, args: argparse.Namespace, console: Any) -> int:

        directory = Path(args.directory)
        if directory.exists():
            console.error(f"Directory '{args.directory}' already exists")
            return 1

        console.info(f"Creating Flaxon project: {args.directory}")

        generator_type = import_attribute("flaxon.cli.generator", "Generator")

        generator = generator_type()

        try:
            generator.generate(directory, args.template)
            console.success(f"Project created at {directory.resolve()}")
            console.info("\nNext steps:")
            console.info(f"  cd {args.directory}")
            console.info("  python -m pip install -e .")
            console.info("  flaxon run app:app --reload")
            return 0
        except Exception as exc:
            console.error(f"Failed to create project: {exc}")
            return 1


class GenerateCommand(Command):
    """Generate command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="generate",
            handler=self._generate,
            help_text="Generate code from templates",
            description="Generate controllers, schemas, services, etc.",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "type", choices=["controller", "schema", "service", "middleware"], help="Type of code to generate"
        )
        parser.add_argument("name", help="Name of the generated component")

    def _generate(self, args: argparse.Namespace, console: Any) -> int:
        generator_type = import_attribute("flaxon.cli.generator", "Generator")

        generator = generator_type()

        try:
            generator.generate_component(args.type, args.name)
            console.success(f"Generated {args.type}: {args.name}")
            return 0
        except Exception as exc:
            console.error(f"Failed to generate: {exc}")
            return 1
