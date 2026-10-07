"""Metric timer histogram behavior and boundary cases."""

import pytest

from flaxon.metrics.timers import Histogram, Timer


def test_timer_statistics_keep_label_groups_separate():
    timer = Timer("latency", labels=["route"])
    for value in [1, 2, 3, 4]:
        timer.observe(value, route="/items")
    timer.observe(100, route="/admin")
    stats = timer.get_stats(route="/items")
    assert stats["count"] == 4 and stats["sum"] == 10 and stats["avg"] == 2.5
    assert stats["min"] == 1 and stats["max"] == 4
    assert timer.get_stats(route="/admin")["count"] == 1


def test_histogram_buckets_are_cumulative_at_boundaries():
    histogram = Histogram("latency", buckets=[1, 5, 10])
    for value in [1, 5, 11]:
        histogram.observe(value)
    assert histogram.get_stats() == {"le_1": 1, "le_5": 2, "le_10": 2, "count": 3, "sum": 17}


def test_context_records_duration_when_body_raises(monkeypatch):
    times = iter([1, 1.25])
    monkeypatch.setattr("flaxon.metrics.timers.time.perf_counter", lambda: next(times))
    timer = Timer("latency")
    with pytest.raises(ValueError):
        with timer.time():
            raise ValueError("failure")
    assert timer.get_stats()["sum"] == 250
