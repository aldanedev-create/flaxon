from __future__ import annotations

import asyncio
import random
import string
import uuid
from datetime import datetime
from typing import Any


class Factory:
    """Factory implementation for the testing subsystem."""

    def __init__(self) -> None:
        self._sequences: dict[str, int] = {}

    def sequence(self, name: str) -> int:
        """Perform the sequence operation for factory."""
        if name not in self._sequences:
            self._sequences[name] = 0
        self._sequences[name] += 1
        return self._sequences[name]

    def random_string(self, length: int = 10) -> str:
        # FIX (S311): Standard pseudo-random generators are safe for test factories
        """Generate a random string for test data."""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def random_email(self) -> str:
        """Generate a random email for test data."""
        domain = random.choice(["example.com", "test.com", "flaxon.dev"])
        return f"{self.random_string(8)}@{domain}"

    def random_int(self, min_val: int = 0, max_val: int = 100) -> int:
        # FIX (A002): Renamed `min`/`max` parameters to avoid shadowing built-ins
        """Generate a random int for test data."""
        return random.randint(min_val, max_val)

    def random_float(self, min_val: float = 0.0, max_val: float = 100.0) -> float:
        # FIX (A002): Renamed `min`/`max` parameters to avoid shadowing built-ins
        """Generate a random float for test data."""
        return random.uniform(min_val, max_val)

    def random_bool(self) -> bool:
        """Generate a random bool for test data."""
        return random.choice([True, False])

    def random_uuid(self) -> str:
        """Generate a random uuid for test data."""
        return str(uuid.uuid4())

    def random_date(self) -> str:
        # FIX (PLC0415): Moved datetime import to top level
        """Generate a random date for test data."""
        return datetime.now().isoformat()

    def build(self, **kwargs: Any) -> dict[str, Any]:
        """Perform the build operation for factory."""
        return kwargs

    def create(self, **kwargs: Any) -> dict[str, Any]:
        """Create a new entry from the supplied values."""
        return self.build(**kwargs)


class ModelFactory(Factory):
    """Model factory implementation for the testing subsystem."""

    def __init__(self, model_class: Any) -> None:
        super().__init__()
        self.model_class = model_class

    def build(self, **kwargs: Any) -> Any:
        """Perform the build operation for model factory."""
        return self.model_class(**kwargs)

    def create(self, **kwargs: Any) -> Any:
        """Create a new entry from the supplied values."""
        instance = self.build(**kwargs)
        if hasattr(instance, "save"):
            save_method = instance.save
            if asyncio.iscoroutinefunction(save_method):
                asyncio.run(save_method())
            else:
                save_method()
        return instance
