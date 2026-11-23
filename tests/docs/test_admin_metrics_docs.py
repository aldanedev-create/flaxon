"""Docs-as-contract: every Python block in the metrics guide executes."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "guides" / "admin-metrics.md"
BLOCKS = re.findall(r"```python\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)


class Order:
    """Stub Tortoise-like model; docs blocks only inspect declarations."""

    @classmethod
    def filter(cls, **kwargs):
        return cls()

    async def count(self):
        return 10

    def annotate(self, **kwargs):
        return self

    def group_by(self, *args):
        return self

    async def values(self, *args):
        return []

    def limit(self, n):
        return self


def _namespace():
    class Dashboard:
        def __init__(self):
            self.registered = []

        def register_metric(self, metric, *, placement="dashboard"):
            metric.placement = placement
            self.registered.append(metric)
            return metric

    return {
        "Order": Order,
        "dashboard": Dashboard(),
        "__name__": "metrics_docs",
    }


def test_guide_has_five_executable_examples():
    assert len(BLOCKS) == 5


def test_minimal_metric_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[0], "admin-metrics.md:block-1", "exec"), namespace)
    assert namespace["value"].kind == "value"
    assert namespace["dashboard"].registered


def test_placement_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[0], "admin-metrics.md:block-1", "exec"), namespace)
    exec(compile(BLOCKS[1], "admin-metrics.md:block-2", "exec"), namespace)
    assert namespace["value"].placement == "order"


def test_five_metric_kinds_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[2], "admin-metrics.md:block-3", "exec"), namespace)
    assert namespace["cards"][2].field == "status"


def test_ranges_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[3], "admin-metrics.md:block-4", "exec"), namespace)
    assert namespace["qtd"].start.month == 4


def test_cache_example_executes():
    namespace = _namespace()
    exec(compile(BLOCKS[4], "admin-metrics.md:block-5", "exec"), namespace)
    assert namespace["cache"].get("orders:value") is None
