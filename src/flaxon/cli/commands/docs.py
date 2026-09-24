from __future__ import annotations

import argparse
import json
from typing import Any

from ..base import Command


class DocsCommand(Command):
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
        from flaxon.openapi import OpenAPIGenerator
        from flaxon.utils.import_string import import_string

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        title = args.title or getattr(app, "name", "Flaxon API")
        generator = OpenAPIGenerator(title=title, version=args.version)

        try:
            spec = generator.generate_from_app(app, include_internal=args.include_internal)
        except Exception as exc:
            console.error(f"Failed to generate OpenAPI spec: {exc}")
            return 1

        indent = args.indent or None
        output = json.dumps(spec, indent=indent)

        if args.check:
            try:
                with open(args.output, encoding="utf-8") as file:
                    existing = json.load(file)
            except FileNotFoundError:
                console.error(f"OpenAPI output does not exist: {args.output}")
                return 1
            except (OSError, json.JSONDecodeError) as exc:
                console.error(f"OpenAPI output is not valid JSON: {exc}")
                return 1
            if existing != spec:
                console.error(f"OpenAPI output is out of date: {args.output}")
                return 1
            console.success(f"OpenAPI spec is current: {args.output}")
            return 0

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)

        path_count = len(spec.get("paths", {}))
        console.success(f"Wrote OpenAPI spec for {path_count} path(s) to {args.output}")
        console.info("Hand-edit this file for anything auto-detection can't infer, or re-run this command to regenerate the basics.")

        return 0
