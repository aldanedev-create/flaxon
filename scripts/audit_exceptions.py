"""Inventory broad handlers, including suppressed exceptions, for manual review."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory() -> dict[str, object]:
    """Report broad catches regardless of whether the exception is named."""
    handlers = []
    suppressions = []
    for path in sorted((ROOT / "src/flaxon").rglob("*.py")):
        source = path.read_text()
        for node in ast.walk(ast.parse(source)):
            if (
                isinstance(node, ast.ExceptHandler)
                and isinstance(node.type, ast.Name)
                and node.type.id == "Exception"
            ):
                handlers.append({
                    "file": path.relative_to(ROOT).as_posix(),
                    "line": node.lineno,
                    "named": node.name is not None,
                    "body": [ast.unparse(statement) for statement in node.body],
                })
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "suppress"
                and any(isinstance(arg, ast.Name) and arg.id == "Exception" for arg in node.args)
            ):
                suppressions.append({"file": path.relative_to(ROOT).as_posix(), "line": node.lineno})
    return {"broad_handlers": len(handlers), "handlers": handlers, "suppressed_exceptions": suppressions}


if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2))
