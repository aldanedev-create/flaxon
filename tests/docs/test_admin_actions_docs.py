"""Docs-as-contract: every Python block in the actions guide executes."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "guides" / "admin-actions.md"
BLOCKS = re.findall(r"```python\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)


class Order:
    """Stub registered model; docs blocks only inspect declarations."""


def _namespace():
    class Dashboard:
        def __init__(self):
            self.registered = []

        def register_action(self, action, model=None):
            self.registered.append((action, model))
            return action

    return {"Order": Order, "dashboard": Dashboard(), "__name__": "actions_docs"}


def test_guide_has_five_executable_examples():
    assert len(BLOCKS) == 5


def test_minimal_action_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[0], "admin-actions.md:block-1", "exec"), namespace)
    assert namespace["action"].get_name() == "mark_reviewed"
    assert namespace["dashboard"].registered


def test_prompt_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[1], "admin-actions.md:block-2", "exec"), namespace)
    assert namespace["prompts"][0].clean("fast") == "fast"


def test_examples_block_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[2], "admin-actions.md:block-3", "exec"), namespace)
    assert namespace["approve"].name == "approve_orders"
    assert namespace["export"].name == "export_csv"


def test_authorization_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[0], "admin-actions.md:block-1", "exec"), namespace)
    exec(compile(BLOCKS[3], "admin-actions.md:block-4", "exec"), namespace)
    assert namespace["guarded"].permission == "order.managers_only_order"


def test_result_types_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[4], "admin-actions.md:block-5", "exec"), namespace)
    assert namespace["ActionResult"].ok("x").kind == "message"
