from __future__ import annotations

import hashlib
import inspect
import json
from typing import Any


class KeyBuilder:
    """Build namespaced cache keys from values and callable arguments."""

    def __init__(self, prefix: str = "cache") -> None:
        self.prefix = prefix

    def build(self, *args: Any, **kwargs: Any) -> str:
        """Join a namespace with positional and sorted keyword values."""
        key_parts = [self.prefix]

        if args:
            key_parts.append(str(args))

        if kwargs:
            key_parts.append(str(sorted(kwargs.items())))

        return ":".join(key_parts)

    def build_from_func(self, func: Any, *args: Any, **kwargs: Any) -> str:
        """Build a key from a callable name and bound arguments, including defaults."""
        key_parts = [self.prefix, func.__name__]

        signature = inspect.signature(func)
        bound_args = signature.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()

        arg_dict = {}
        for name, value in bound_args.arguments.items():
            try:
                json.dumps(value)
                arg_dict[name] = value
            except TypeError:
                arg_dict[name] = str(value)

        if arg_dict:
            key_parts.append(json.dumps(arg_dict, sort_keys=True, default=str))

        return ":".join(key_parts)

    def build_hash(self, *args: Any, **kwargs: Any) -> str:
        """Return the MD5 digest of the constructed cache key."""
        key = self.build(*args, **kwargs)
        return hashlib.md5(key.encode()).hexdigest()

    def build_hash_from_func(self, func: Any, *args: Any, **kwargs: Any) -> str:
        """Return the MD5 digest of a callable-specific cache key."""
        key = self.build_from_func(func, *args, **kwargs)
        return hashlib.md5(key.encode()).hexdigest()

    def with_prefix(self, prefix: str) -> KeyBuilder:
        """Create a key builder with an additional namespace component."""
        return KeyBuilder(f"{self.prefix}:{prefix}")

    def build_key(self, key: str) -> str:
        """Prepend this builder's namespace to an existing key."""
        return f"{self.prefix}:{key}"

    def get_prefix(self) -> str:
        """Return the namespace used by this builder."""
        return self.prefix


class CacheKeyBuilder(KeyBuilder):
    """Build cache keys scoped to a user, path, or query."""

    def __init__(self, prefix: str = "cache") -> None:
        super().__init__(prefix)

    def for_user(self, user_id: str | int, *args: Any, **kwargs: Any) -> str:
        """Build a cache key containing the user identifier."""
        key_parts = [self.prefix, "user", str(user_id)]

        if args:
            key_parts.append(str(args))
        if kwargs:
            key_parts.append(str(sorted(kwargs.items())))

        return ":".join(key_parts)

    def for_path(self, path: str, *args: Any, **kwargs: Any) -> str:
        """Build a cache key containing the request path."""
        key_parts = [self.prefix, "path", path]

        if args:
            key_parts.append(str(args))
        if kwargs:
            key_parts.append(str(sorted(kwargs.items())))

        return ":".join(key_parts)

    def for_query(self, query: str, *args: Any, **kwargs: Any) -> str:
        """Build a cache key containing the query text."""
        key_parts = [self.prefix, "query", query]

        if args:
            key_parts.append(str(args))
        if kwargs:
            key_parts.append(str(sorted(kwargs.items())))

        return ":".join(key_parts)
