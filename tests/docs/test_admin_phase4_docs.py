"""Docs-as-contract: every Python block in the filters/safety guide executes."""

from __future__ import annotations

import re
from pathlib import Path

from flaxon import Flaxon

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "guides" / "admin-filters-and-safety.md"
BLOCKS = re.findall(r"```python\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)


class Order:
    """Stub registered model; the guide blocks only inspect declarations."""


class Dashboard:
    def __init__(self):
        self.registered = []

    def register(self, model, **options):
        self.registered.append((model, options))
        return model


def _namespace():
    return {"Order": Order, "dashboard": Dashboard(), "app": Flaxon("docs"), "__name__": "filters_docs"}


def test_guide_has_six_executable_examples():
    assert len(BLOCKS) == 6


def test_filter_block_filters_rows():
    namespace = _namespace()
    exec(compile(BLOCKS[0], "admin-filters-and-safety.md:block-1", "exec"), namespace)
    assert [row["id"] for row in namespace["selected"]] == [3]


def test_filter_registration_block_executes():
    namespace = _namespace()
    # Block 2 reuses the filter classes imported by block 1.
    exec(compile(BLOCKS[0], "admin-filters-and-safety.md:block-1", "exec"), namespace)
    exec(compile(BLOCKS[1], "admin-filters-and-safety.md:block-2", "exec"), namespace)
    _, options = namespace["dashboard"].registered[0]
    assert [filt.field for filt in options["filters"]] == ["status", "fulfilled"]


def test_lens_block_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[2], "admin-filters-and-safety.md:block-3", "exec"), namespace)
    assert namespace["unpaid"].name == "unpaid"
    assert namespace["dashboard"].registered


def test_import_block_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[3], "admin-filters-and-safety.md:block-4", "exec"), namespace)
    assert namespace["mapped"] == [{"reference": "ORD-1"}]
    assert namespace["safe"].startswith("'=")


def test_policy_block_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[4], "admin-filters-and-safety.md:block-5", "exec"), namespace)
    policy = namespace["policy"]
    assert policy.allows("delete", "user", {}) is False
    assert policy.allows("view", "user", {"status": "archived"}) is False
    assert policy.allows("view", "user", {"status": "open"}) is True


def test_impersonation_config_block_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[5], "admin-filters-and-safety.md:block-6", "exec"), namespace)
    dashboard = namespace["dashboard"]
    assert dashboard.config.allow_impersonation is True
    assert dashboard.impersonation.enabled is True
