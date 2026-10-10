from __future__ import annotations

import re
from typing import Any, ClassVar


class Redactor:
    """Redactor implementation for the debugging subsystem."""

    SENSITIVE_KEYS: ClassVar[Any] = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "authorization",
        "auth",
        "api_key",
        "apikey",
        "private_key",
        "private",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
        "social_security",
        "phone",
        "email",
        "address",
        "cookie",
        "set_cookie",
        "x_api_key",
        "x_apikey",
        "bearer",
        "jwt",
        "access_token",
        "refresh_token",
    }

    SENSITIVE_PATTERNS: ClassVar[Any] = [
        ("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", "[EMAIL]"),
        ("\\b\\d{3}-\\d{2}-\\d{4}\\b", "[SSN]"),
        ("\\b\\d{4}-\\d{4}-\\d{4}-\\d{4}\\b", "[CREDIT_CARD]"),
        ("\\b[A-Za-z0-9+/]{40,}={0,2}\\b", "[TOKEN]"),
        ("\\beyJ[A-Za-z0-9_-]+\\b", "[TOKEN]"),
        ("\\b(?:secret|token)[A-Za-z0-9_-]+\\b", "[REDACTED]"),
        ("\\b[0-9a-f]{32,}\\b", "[HASH]"),
        ("\\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b", "[UUID]"),
    ]

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def redact(self, value: Any, depth: int = 0) -> Any:
        """Perform the redact operation for redactor."""
        if not self.enabled:
            return value

        if depth > 5:
            return "[TRUNCATED]"

        if isinstance(value, dict):
            return {
                str(key): "[REDACTED]" if self._is_sensitive(key) else self.redact(item, depth + 1)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [self.redact(item, depth + 1) for item in value[:50]]

        if isinstance(value, str):
            return self._redact_string(value)

        return value

    def _is_sensitive(self, key: str) -> bool:
        normalized = key.lower().replace("-", "_").replace(" ", "_")
        return any(part in normalized for part in self.SENSITIVE_KEYS)

    def _redact_string(self, value: str) -> str:
        truncated = len(value) > 1000
        result = value[:1000] if truncated else value

        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result)

        if truncated:
            result += "...[TRUNCATED]"

        return result

    def redact_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Perform the redact headers operation for redactor."""
        result = {}
        for key, value in headers.items():
            if self._is_sensitive(key):
                result[key] = "[REDACTED]"
            else:
                result[key] = value
        return result

    def redact_url(self, url: str) -> str:
        """Perform the redact url operation for redactor."""
        return re.sub(r"([?&][^=]+=)[^&]+", r"\1[REDACTED]", url)


_default_redactor = Redactor()


def redact(value: Any, enabled: bool = True) -> Any:
    """Perform the redact operation for this subsystem."""
    if enabled:
        return _default_redactor.redact(value)
    return value


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Perform the redact headers operation for this subsystem."""
    return _default_redactor.redact_headers(headers)


def redact_url(url: str) -> str:
    """Perform the redact url operation for this subsystem."""
    return _default_redactor.redact_url(url)
