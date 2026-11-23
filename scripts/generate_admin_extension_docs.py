"""Generate ``docs/api/admin-extensions.md`` from the extension module.

The page is derived from ``__all__``, signatures and docstrings, so the
documented API cannot drift from the code. Run with ``--check`` in CI to fail
when the file is stale.
"""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flaxon.admin import extensions  # noqa: E402

OUTPUT = ROOT / "docs" / "api" / "admin-extensions.md"
HEADER = """# Admin extension API

Generated from `flaxon.admin.extensions` by `scripts/generate_admin_extension_docs.py`.
Do not edit by hand: run the script (or `python scripts/generate_admin_extension_docs.py --check`).
"""


def _signature(target: Any) -> str:
    try:
        signature = inspect.signature(target, eval_str=True)
    except (TypeError, ValueError, NameError):
        return ""
    text = str(signature).replace("flaxon.admin.extensions.", "").replace("flaxon.admin.", "")
    return text.replace("'", "").replace("(self, ", "(").replace("(self)", "()")


def _summary(target: Any) -> str:
    doc = inspect.getdoc(target) or ""
    paragraph = doc.split("\n\n", 1)[0].strip()
    return " ".join(paragraph.split())


def _public_members(cls: type) -> list[Any]:
    members = []
    for name, value in vars(cls).items():
        if name.startswith("_") or not callable(value):
            continue
        if getattr(value, "__doc__", None) is None:
            continue
        members.append(value)
    return sorted(members, key=lambda item: item.__name__)


def render() -> str:
    """Return the complete Markdown page."""
    lines = [HEADER]
    for name in sorted(extensions.__all__):
        target = getattr(extensions, name)
        if isinstance(target, str):
            lines.append(f"## `{name}`\n\nConstant: `{target}`.\n")
            continue
        if inspect.isclass(target):
            lines.append(f"## `{name}`\n")
            lines.append(f"`class {name}{_signature(target)}`\n")
            summary = _summary(target)
            if summary:
                lines.append(f"{summary}\n")
            for member in _public_members(target):
                lines.append(f"### `{member.__name__}`\n")
                lines.append(f"`{member.__name__}{_signature(member)}`\n")
                member_summary = _summary(member)
                if member_summary:
                    lines.append(f"{member_summary}\n")
            continue
        if callable(target):
            lines.append(f"## `{name}`\n")
            lines.append(f"`{name}{_signature(target)}`\n")
            summary = _summary(target)
            if summary:
                lines.append(f"{summary}\n")
            continue
        lines.append(f"## `{name}`\n\nValue: `{target!r}`.\n")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    """Write the page, or verify it with ``--check``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the file is stale")
    arguments = parser.parse_args()
    rendered = render()
    if arguments.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != rendered:
            print(f"{OUTPUT.relative_to(ROOT)} is stale; run scripts/generate_admin_extension_docs.py")
            return 1
        print(f"{OUTPUT.relative_to(ROOT)} is current")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
