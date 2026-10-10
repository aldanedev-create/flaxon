from __future__ import annotations

import threading
import time
from typing import Any


class Timer:
    """Timer implementation for the metrics subsystem."""

    def __init__(self, name: str, help_text: str = "", labels: list[str] | None = None) -> None:
        self.name = name
        self.help_text = help_text
        self.labels = labels or []
        self._values: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _key(self, **labels: Any) -> str:
        if not self.labels:
            return ""
        return ",".join(f"{k}={labels.get(k)}" for k in self.labels)

    def observe(self, duration: float, **labels: Any) -> None:
        """Perform the observe operation for timer."""
        key = self._key(**labels)
        with self._lock:
            if key not in self._values:
                self._values[key] = []
            self._values[key].append(duration)

    def time(self, **labels: Any) -> TimerContext:
        """Perform the time operation for timer."""
        return TimerContext(self, **labels)

    def get_stats(self, **labels: Any) -> dict[str, float]:
        """Return the stats."""
        key = self._key(**labels)
        values = self._values.get(key, [])

        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}

        sorted_values = sorted(values)
        count = len(values)
        total = sum(values)

        return {
            "count": count,
            "sum": total,
            "avg": total / count,
            "min": min(values),
            "max": max(values),
            "p50": sorted_values[int(count * 0.50)],
            "p90": sorted_values[int(count * 0.90)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """Return the all stats."""
        result = {}
        keys = list(self._values.keys())
        for key in keys:
            labels = {}
            if key:
                for pair in key.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        labels[k] = v
            result[key] = self.get_stats(**labels)
        return result

    def get_metrics(self) -> dict[str, Any]:
        """Return the metrics."""
        return {
            "name": self.name,
            "help": self.help_text,
            "stats": self.get_all_stats(),
        }


class TimerContext:
    """Timer context implementation for the metrics subsystem."""

    def __init__(self, timer: Timer, **labels: Any) -> None:
        self.timer = timer
        self.labels = labels
        self._start: float | None = None

    def __enter__(self) -> TimerContext:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._start is not None:
            duration = (time.perf_counter() - self._start) * 1000
            self.timer.observe(duration, **self.labels)


class Histogram:
    """Histogram implementation for the metrics subsystem."""

    def __init__(
        self,
        name: str,
        help_text: str = "",
        labels: list[str] | None = None,
        buckets: list[float] | None = None,
    ) -> None:
        self.name = name
        self.help_text = help_text
        self.labels = labels or []
        self.buckets = buckets or [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
        self._values: dict[str, dict[str, int | float]] = {}
        self._lock = threading.Lock()

    def _key(self, **labels: Any) -> str:
        if not self.labels:
            return ""
        return ",".join(f"{k}={labels.get(k)}" for k in self.labels)

    def observe(self, value: float, **labels: Any) -> None:
        """Perform the observe operation for histogram."""
        key = self._key(**labels)
        with self._lock:
            if key not in self._values:
                self._values[key] = {f"le_{b}": 0 for b in self.buckets}
                self._values[key]["count"] = 0
                self._values[key]["sum"] = 0.0

            for bucket in self.buckets:
                if value <= bucket:
                    self._values[key][f"le_{bucket}"] += 1

            self._values[key]["count"] += 1
            self._values[key]["sum"] += value

    def get_stats(self, **labels: Any) -> dict[str, Any]:
        """Return the stats."""
        key = self._key(**labels)
        return dict(self._values.get(key, {}))

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Return the all stats."""
        return dict(self._values)

    def get_metrics(self) -> dict[str, Any]:
        """Return the metrics."""
        return {
            "name": self.name,
            "help": self.help_text,
            "buckets": self.buckets,
            "values": dict(self._values),
        }
