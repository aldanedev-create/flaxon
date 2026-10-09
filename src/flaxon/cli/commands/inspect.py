from __future__ import annotations

import argparse
import json
from typing import Any

from ..base import Command


class InspectCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="inspect",
            handler=self._run,
            help_text="Inspect application internals",
            description="Show detailed application information",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument("--middleware", action="store_true", help="Show middleware stack")
        parser.add_argument("--config", action="store_true", help="Show configuration")
        parser.add_argument(
            "--format", choices=["json", "yaml", "table"], default="table", help="Output format"
        )

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        from flaxon.utils.import_string import import_string

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        data = {"name": app.name, "debug": app.debug}

        if args.middleware:
            data["middleware"] = [str(m) for m in app._middleware]

        if args.config:
            data["config"] = dict(app.config)

        if args.format == "json":
            print(json.dumps(data, indent=2, default=str))
        elif args.format == "yaml":
            try:
                import yaml

                print(yaml.dump(data))
            except ImportError:
                console.warning("yaml not installed, falling back to json")
                print(json.dumps(data, indent=2, default=str))
        else:
            console.info(f"Application: {data['name']}")
            console.info(f"Debug: {data['debug']}")
            if args.middleware and "middleware" in data:
                console.info("Middleware:")
                for m in data["middleware"]:
                    console.info(f"  - {m}")
            if args.config and "config" in data:
                console.info("Config:")
                for k, v in data["config"].items():
                    console.info(f"  {k}: {v}")

        return 0
