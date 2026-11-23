"""Docs-as-contract and drift checks for the Phase 6 AI documentation.

Every Python block in the tutorial ladder, cookbook and AI recipes is executed
here, and the generated AI docs must match what the generator produces.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from flaxon import __version__

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_ai_docs  # noqa: E402 - local generator module

DOCS_WITH_BLOCKS = [
    "tutorial-ladder.md",
    "cookbook.md",
    "ai/recipes/api.md",
    "ai/recipes/database.md",
    "ai/recipes/admin-resource.md",
    "ai/recipes/metric.md",
    "ai/recipes/action.md",
    "ai/recipes/teloce-field.md",
    "ai/recipes/websocket-room.md",
]


def _base_namespace(name: str) -> dict[str, Any]:
    """A fresh namespace shared by all blocks within one document."""
    return {
        "__name__": name,
        "__builtins__": __builtins__,
    }


def _blocks(doc: str) -> list[str]:
    text = (ROOT / "docs" / doc).read_text(encoding="utf-8")
    return re.findall(r"```python\n(.*?)```", text, re.S)


def test_every_generated_file_matches_the_code():
    for name, expected in generate_ai_docs.render_all().items():
        path = ROOT / name
        assert path.is_file(), f"{name} is missing; run scripts/generate_ai_docs.py"
        assert path.read_text(encoding="utf-8") == expected, f"{name} is stale"


def test_all_pitfall_facts_are_verified():
    assert generate_ai_docs.verify_pitfalls() == []


def test_llms_full_is_version_stamped():
    text = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
    assert f"version {__version__}" in text.splitlines()[0]


def test_llms_txt_lists_every_core_and_recipe_doc():
    text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for doc in generate_ai_docs.CORE_DOCS + generate_ai_docs.GENERATED_DOCS:
        assert f"]({doc})" in text
    for recipe in (ROOT / "docs" / "ai" / "recipes").glob("*.md"):
        assert f"docs/ai/recipes/{recipe.name}" in text


def test_every_documented_python_block_executes():
    """Compile and run each block in order within a per-document namespace."""
    executed = 0
    for doc in DOCS_WITH_BLOCKS:
        blocks = _blocks(doc)
        assert blocks, f"no Python blocks in {doc}"
        namespace = _base_namespace(f"doc_{doc.replace('/', '_').replace('.', '_')}")
        for index, block in enumerate(blocks, 1):
            code = compile(block, f"{doc}:block-{index}", "exec")
            exec(code, namespace)
            executed += 1
    assert executed >= 20


def test_database_recipe_reuses_one_event_loop():
    """The database recipe's asyncio.run must not be nested in a running loop."""
    # Guard against future refactors that make the recipe use await at import.
    namespace = _base_namespace("db_recipe_check")
    for block in _blocks("ai/recipes/database.md"):
        exec(compile(block, "database.md", "exec"), namespace)
