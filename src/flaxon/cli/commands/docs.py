from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute
from flaxon.cli.base import Command


class DocsCommand(Command):
    """Docs command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="docs",
            handler=self._run,
            help_text="Generate OpenAPI docs from your app's routes, docstrings, and schemas",
            description=(
                "Auto-generates an OpenAPI spec by introspecting your application's "
                "registered routes, endpoint docstrings, and Schema-typed parameters -- "
                "no hand-written descriptions needed for the basics. Writes it to a file "
                "you can hand-edit afterward for anything the auto-detection can't infer "
                "(security schemes, examples, descriptions on bare-typed parameters, etc.)."
            ),
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument(
            "-o", "--output", default="openapi.json", help="Output file path (default: openapi.json)"
        )
        parser.add_argument("--title", default=None, help="API title (default: the app's name)")
        parser.add_argument("--version", default="1.0.0", help="API version (default: 1.0.0)")
        parser.add_argument(
            "--indent", type=int, default=2, help="JSON indent width, 0 for compact output (default: 2)"
        )
        parser.add_argument(
            "--include-internal",
            action="store_true",
            help="Include Flaxon's own system routes (/health, /metrics, /docs, etc.) in the spec",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Verify the existing output matches the generated spec without rewriting it",
        )

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        open_apigenerator_type = import_attribute("flaxon.openapi", "OpenAPIGenerator")
        import_string = import_attribute("flaxon.utils.import_string", "import_string")

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        title = args.title or getattr(app, "name", "Flaxon API")
        generator = open_apigenerator_type(title=title, version=args.version)

        try:
            spec = generator.generate_from_app(app, include_internal=args.include_internal)
        except Exception as exc:
            console.error(f"Failed to generate OpenAPI spec: {exc}")
            return 1

        indent = args.indent or None
        output = json.dumps(spec, indent=indent)

        if args.check:
            return self._check_output(args.output, spec, console)

        with Path(args.output).open("w", encoding="utf-8") as f:
            f.write(output)

        path_count = len(spec.get("paths", {}))
        console.success(f"Wrote OpenAPI spec for {path_count} path(s) to {args.output}")
        console.info(
            "Hand-edit this file for anything auto-detection can't infer,"
            " or re-run this command to regenerate the basics."
        )

        return 0

    @staticmethod
    def _check_output(output_path: str, spec: dict, console: Any) -> int:
        try:
            with Path(output_path).open(encoding="utf-8") as file:
                existing = json.load(file)
        except FileNotFoundError:
            console.error(f"OpenAPI output does not exist: {output_path}")
            return 1
        except (OSError, json.JSONDecodeError) as exc:
            console.error(f"OpenAPI output is not valid JSON: {exc}")
            return 1
        if existing != spec:
            console.error(f"OpenAPI output is out of date: {output_path}")
            return 1
        console.success(f"OpenAPI spec is current: {output_path}")
        return 0
