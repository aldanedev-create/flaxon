"""Metric counter labels behavior and boundary cases."""

from concurrent.futures import ThreadPoolExecutor

from flaxon.metrics.counters import Counter


def test_label_sets_have_independent_counts():
    counter = Counter("requests", labels=["method", "status"])
    counter.inc(2, method="GET", status=200)
    counter.inc(method="POST", status=201)
    assert counter.get(method="GET", status=200) == 2
    assert counter.get(method="POST", status=201) == 1
    assert counter.get(method="GET", status=404) == 0
    counter.reset(method="GET", status=200)
    assert counter.get(method="POST", status=201) == 1


def test_parallel_thread_increments_are_not_lost():
    counter = Counter("requests")
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: counter.inc(), range(1000)))
    assert counter.get() == 1000


def test_export_returns_copy_of_counter_values():
    counter = Counter("requests")
    counter.inc()
    exported = counter.get_all()
    exported[""] = 99
    assert counter.get() == 1
