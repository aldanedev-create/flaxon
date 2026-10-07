"""Metric gauge values behavior and boundary cases."""

from flaxon.metrics.counters import Gauge


def test_gauge_supports_fractional_increments_and_decrements():
    gauge = Gauge("load")
    gauge.set(1.5)
    gauge.inc(0.25)
    gauge.dec(0.5)
    assert gauge.get() == 1.25


def test_setting_zero_only_changes_target_label():
    gauge = Gauge("workers", labels=["queue"])
    gauge.set(2, queue="fast")
    gauge.set(3, queue="slow")
    gauge.set(0, queue="fast")
    assert gauge.get(queue="fast") == 0 and gauge.get(queue="slow") == 3


def test_export_contains_help_and_isolated_values():
    gauge = Gauge("load", "active load")
    gauge.set(2)
    snapshot = gauge.get_metrics()
    snapshot["values"][""] = 9
    assert gauge.get() == 2 and snapshot["help"] == "active load"
