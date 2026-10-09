"""Multi-value query parameter mapping."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from urllib.parse import parse_qs


class QueryParams(Mapping[str, str]):
    """Read URL query parameters while retaining repeated values."""

    def __init__(self, value: bytes | str | Mapping[str, str] | None = None) -> None:
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        self._data = (
            parse_qs(value, keep_blank_values=True)
            if isinstance(value, str)
            else {key: [item] for key, item in (value or {}).items()}
        )

    def __getitem__(self, key: str) -> str:
        return self._data[key][-1]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def getlist(self, key: str) -> list[str]:
        """Return all values supplied for a key."""
        return list(self._data.get(key, []))
