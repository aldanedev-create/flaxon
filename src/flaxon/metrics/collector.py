from __future__ import annotations

import time
from typing import Any

from .counters import Counter, Gauge
from .timers import Histogram, Timer


class MetricsCollector:
    """Metrics collector implementation for the metrics subsystem."""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._timers: dict[str, Timer] = {}
        self._histograms: dict[str, Histogram] = {}

    def counter(self, name: str, help_text: str = "", labels: list[str] | None = None) -> Counter:
        """Perform the counter operation for metrics collector."""
        if name not in self._counters:
            self._counters[name] = Counter(name, help_text, labels or [])
        return self._counters[name]

    def gauge(self, name: str, help_text: str = "", labels: list[str] | None = None) -> Gauge:
        """Perform the gauge operation for metrics collector."""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, help_text, labels or [])
        return self._gauges[name]

    def timer(self, name: str, help_text: str = "", labels: list[str] | None = None) -> Timer:
        """Perform the timer operation for metrics collector."""
        if name not in self._timers:
            self._timers[name] = Timer(name, help_text, labels or [])
        return self._timers[name]

    def histogram(
        self,
        name: str,
        help_text: str = "",
        labels: list[str] | None = None,
        buckets: list[float] | None = None,
    ) -> Histogram:
        """Perform the histogram operation for metrics collector."""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, help_text, labels or [], buckets)
        return self._histograms[name]

    def increment(self, name: str, value: int = 1, **labels: Any) -> None:
        """Perform the increment operation for metrics collector."""
        counter = self._counters.get(name)
        if counter:
            counter.inc(value, **labels)

    def decrement(self, name: str, value: int = 1, **labels: Any) -> None:
        """Perform the decrement operation for metrics collector."""
        counter = self._counters.get(name)
        if counter:
            counter.dec(value, **labels)

    def set_gauge(self, name: str, value: float, **labels: Any) -> None:
        """Set the gauge."""
        gauge = self._gauges.get(name)
        if gauge:
            gauge.set(value, **labels)

    def observe_timer(self, name: str, duration: float, **labels: Any) -> None:
        """Observe the timer."""
        timer = self._timers.get(name)
        if timer:
            timer.observe(duration, **labels)

    def observe_histogram(self, name: str, value: float, **labels: Any) -> None:
        """Observe the histogram."""
        histogram = self._histograms.get(name)
        if histogram:
            histogram.observe(value, **labels)

    def time(self, name: str, **labels: Any) -> TimerContext:
        """Perform the time operation for metrics collector."""
        return TimerContext(self, name, **labels)

    def get_metrics(self) -> dict[str, Any]:
        """Return the metrics."""
        result = {}

        for name, counter in self._counters.items():
            result[f"counter_{name}"] = counter.get_metrics()

        for name, gauge in self._gauges.items():
            result[f"gauge_{name}"] = gauge.get_metrics()

        for name, timer in self._timers.items():
            result[f"timer_{name}"] = timer.get_metrics()

        for name, histogram in self._histograms.items():
            result[f"histogram_{name}"] = histogram.get_metrics()

        return result

    def clear(self) -> None:
        """Remove the stored entries."""
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()
        self._histograms.clear()


class TimerContext:
    """Timer context implementation for the metrics subsystem."""

    def __init__(self, collector: MetricsCollector, name: str, **labels: Any) -> None:
        self.collector = collector
        self.name = name
        self.labels = labels
        self._start: float | None = None

    def __enter__(self) -> TimerContext:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._start is not None:
            duration = (time.perf_counter() - self._start) * 1000
            timer = self.collector._timers.get(self.name)
            if timer:
                timer.observe(duration, **self.labels)

    async def __aenter__(self) -> TimerContext:
        self._start = time.perf_counter()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._start is not None:
            duration = (time.perf_counter() - self._start) * 1000
            timer = self.collector._timers.get(self.name)
            if timer:
                timer.observe(duration, **self.labels)
