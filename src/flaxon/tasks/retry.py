from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any


class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 60.0,
        random_jitter: float = 0.1,
        retry_on: list[type[Exception]] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.random_jitter = random_jitter
        self.retry_on = retry_on or [Exception]

    def should_retry(self, retry_count: int, error: Exception) -> bool:
        if retry_count >= self.max_retries:
            return False

        for exc_type in self.retry_on:
            if isinstance(error, exc_type):
                return True

        return False

    def get_delay(self, retry_count: int) -> float:
        if retry_count == 0:
            return self.delay

        delay = self.delay * (self.backoff ** (retry_count - 1))
        delay = min(delay, self.max_delay)

        if self.random_jitter:
            jitter = random.uniform(-self.random_jitter, self.random_jitter)
            delay = delay * (1 + jitter)

        return max(0, delay)

    def get_next_retry_count(self, retry_count: int) -> int:
        return retry_count + 1


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    random_jitter: float = 0.1,
    retry_on: list[type[Exception]] | None = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        policy = RetryPolicy(
            max_retries=max_retries,
            delay=delay,
            backoff=backoff,
            max_delay=max_delay,
            random_jitter=random_jitter,
            retry_on=retry_on,
        )

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_count = 0

            while True:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, func, *args, **kwargs)

                except Exception as exc:
                    if not policy.should_retry(retry_count, exc):
                        raise

                    retry_count += 1
                    delay_seconds = policy.get_delay(retry_count)
                    await asyncio.sleep(delay_seconds)

        return wrapper
    return decorator
