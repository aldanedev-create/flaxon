from __future__ import annotations

import os
import secrets
import string


class SecretManager:
    """Secret manager implementation for the security subsystem."""

    def __init__(self, env_prefix: str = "SECRET_") -> None:
        self.env_prefix = env_prefix

    def get(self, name: str, default: str | None = None) -> str | None:
        """Retrieve the requested value using this object's configured behavior."""
        env_key = f"{self.env_prefix}{name.upper()}"
        value = os.environ.get(env_key)
        if value:
            return value
        return default

    def get_required(self, name: str) -> str:
        """Return the required."""
        env_key = f"{self.env_prefix}{name.upper()}"
        value = os.environ.get(env_key)
        if not value:
            raise ValueError(f"Required secret '{name}' not found in environment")
        return value

    def generate(self, length: int = 32, include_symbols: bool = True) -> str:
        """Perform the generate operation for secret manager."""
        alphabet = string.ascii_letters + string.digits
        if include_symbols:
            alphabet += string.punctuation
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_hex(self, length: int = 32) -> str:
        """Generate the hex."""
        return secrets.token_hex(length // 2)

    def generate_urlsafe(self, length: int = 32) -> str:
        """Generate the urlsafe."""
        return secrets.token_urlsafe(length)


_default_secret_manager = SecretManager()


def get_secret(name: str, default: str | None = None) -> str | None:
    """Return the secret."""
    return _default_secret_manager.get(name, default)


def get_required_secret(name: str) -> str:
    """Return the required secret."""
    return _default_secret_manager.get_required(name)


def generate_secret(length: int = 32, include_symbols: bool = True) -> str:
    """Generate the secret."""
    return _default_secret_manager.generate(length, include_symbols)


def generate_hex_secret(length: int = 32) -> str:
    """Generate the hex secret."""
    return _default_secret_manager.generate_hex(length)


def generate_urlsafe_secret(length: int = 32) -> str:
    """Generate the urlsafe secret."""
    return _default_secret_manager.generate_urlsafe(length)
