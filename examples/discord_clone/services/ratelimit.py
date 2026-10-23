"""Tiny in-process sliding-window rate limiter.

Flaxon ships a RateLimiter, but it is process-local and keyed by client IP
only. For auth endpoints we want per-(IP, action) buckets with clear,
testable semantics, so we keep a small one here. In production you would
back this with Redis so the limit is enforced across workers.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

    def retry_after(self, key: str) -> float:
        bucket = self._hits[key]
        if len(bucket) < self.max_requests:
            return 0.0
        return max(0.0, self.window_seconds - (time.monotonic() - bucket[0]))
