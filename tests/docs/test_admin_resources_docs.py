"""Docs-as-contract: every Python block in the Resource guide executes."""

from __future__ import annotations

import re
from pathlib import Path

from flaxon.admin.registry import Registry

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "guides" / "admin-resources.md"
BLOCKS = re.findall(r"```python\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)


class StubModel:
    pass


def _namespace():
    registry = Registry()

    class Dashboard:
        def register(self, resource):
            resource.model = StubModel
            registry.register(resource())

    return {
        "Customer": StubModel,
        "Order": StubModel,
        "dashboard": Dashboard(),
        "registry": registry,
        "__name__": "resource_docs",
    }


def test_guide_has_four_executable_examples():
    assert len(BLOCKS) == 4


def test_minimal_example_registers_in_under_ten_lines():
    code = BLOCKS[0]
    assert len([line for line in code.splitlines() if line.strip()]) <= 9
    namespace = _namespace()
    exec(compile(code, "admin-resources.md:block-1", "exec"), namespace)
    assert namespace["registry"].get("customer") is not None


def test_field_options_example_validates_as_documented():
    namespace = _namespace()
    exec(compile(BLOCKS[1], "admin-resources.md:block-2", "exec"), namespace)
    assert namespace["cleaned"]["total"] == 42


def test_relation_example_matches_prefetch_behavior():
    namespace = _namespace()
    exec(compile(BLOCKS[2], "admin-resources.md:block-3", "exec"), namespace)
    assert namespace["OrderResource"]().select_related_names() == ["customer"]


def test_validation_failure_example_matches_documented_errors():
    namespace = _namespace()
    exec(compile(BLOCKS[3], "admin-resources.md:block-4", "exec"), namespace)
    assert "email" in namespace["errors"]
