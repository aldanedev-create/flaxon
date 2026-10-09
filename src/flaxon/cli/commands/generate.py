from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..base import Command
from ..generator import Generator


class GenerateCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="generate",
            handler=self._run,
            help_text="Generate code from templates",
            description="Generate controllers, schemas, services, etc.",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "type",
            choices=["controller", "schema", "service", "middleware", "model", "task"],
            help="Type of code to generate",
        )
        parser.add_argument("name", help="Name of the generated component")
        parser.add_argument("--path", default=".", help="Output path")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        generator = Generator()
        path = Path(args.path)

        try:
            if args.type == "model":
                self._generate_model(args.name, path)
            else:
                generator.generate_component(args.type, args.name, path)

            console.success(f"Generated {args.type}: {args.name}")
            return 0
        except Exception as exc:
            console.error(f"Failed to generate: {exc}")
            return 1

    def _generate_model(self, name: str, path: Path) -> None:
        template = f"""class {name.capitalize()}(Schema):
    id = fields.Integer(required=True)
    name = fields.StrField(required=True, max_length=255)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
"""
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{name}_model.py"
        file_path.write_text(template, encoding="utf-8")
