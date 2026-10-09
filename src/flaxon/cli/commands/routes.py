from __future__ import annotations

import argparse
from typing import Any

from flaxon.cli.base import Command


class RoutesCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="routes",
            handler=self._run,
            help_text="List registered HTTP and WebSocket routes",
            description="Display all registered routes in the application",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument(
            "--format", choices=["table", "json", "csv"], default="table", help="Output format"
        )
        parser.add_argument("--output", help="Output file path")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        from flaxon.utils.import_string import import_string

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        console.info(f"Routes for {app.name}")

        rows = []

        for route in app.router.routes:
            methods = ",".join(sorted(route.methods))
            rows.append([methods, route.path, route.name or ""])

        for route in app.router.websocket_routes:
            rows.append(["WEBSOCKET", route.path, route.name or ""])

        if args.format == "json":
            import json

            output = json.dumps({"routes": rows}, indent=2)
        elif args.format == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Method", "Path", "Name"])
            writer.writerows(rows)
            output = output.getvalue()
        else:
            if rows:
                console.table(["Method", "Path", "Name"], rows)
            else:
                console.info("No routes registered")
            return 0

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            console.success(f"Routes written to {args.output}")
        else:
            print(output)

        return 0
