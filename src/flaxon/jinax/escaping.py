from __future__ import annotations

import re
import urllib.parse
from typing import Any, ClassVar


class Escaper:
    """Escaper implementation for the jinax subsystem."""

    HTML_ESCAPE: ClassVar[Any] = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}

    HTML_UNESCAPE: ClassVar[Any] = {v: k for k, v in HTML_ESCAPE.items()}

    @classmethod
    def escape_html(cls, value: str) -> str:
        """Escape the html."""
        if not value:
            return value
        return "".join(cls.HTML_ESCAPE.get(c, c) for c in value)

    @classmethod
    def unescape_html(cls, value: str) -> str:
        """Perform the unescape html operation for escaper."""
        if not value:
            return value
        for escaped, original in cls.HTML_UNESCAPE.items():
            value = value.replace(escaped, original)
        return value

    @classmethod
    def escape_js(cls, value: str) -> str:
        """Escape the js."""
        if not value:
            return value
        replacements = {
            "\\": "\\\\",
            "'": "\\'",
            '"': '\\"',
            "\r": "\\r",
            "\n": "\\n",
        }
        return "".join(replacements.get(character, character) for character in value)

    @classmethod
    def escape_css(cls, value: str) -> str:
        """Escape the css."""
        if not value:
            return value
        # Terminate hex escapes so a following hex digit cannot extend them.
        return re.sub(r"[^a-zA-Z0-9]", lambda m: f"\\{ord(m.group(0)):x} ", value)

    @classmethod
    def escape_url(cls, value: str) -> str:
        """Escape the url."""
        return urllib.parse.quote(value, safe="")

    @classmethod
    def unescape_url(cls, value: str) -> str:
        """Perform the unescape url operation for escaper."""
        return urllib.parse.unquote(value)

    @classmethod
    def escape_xml(cls, value: str) -> str:
        """Escape the xml."""
        return cls.escape_html(value)

    @classmethod
    def escape_attribute(cls, value: str) -> str:
        """Escape the attribute."""
        return cls.escape_html(value)


class SafeString:
    """Safe string implementation for the jinax subsystem."""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"SafeString({self._value!r})"

    def __add__(self, other: Any) -> SafeString:
        """Perform the   add   operation for safe string."""
        if isinstance(other, SafeString):
            return SafeString(self._value + other._value)
        return SafeString(self._value + str(other))

    def __radd__(self, other: Any) -> SafeString:
        return SafeString(str(other) + self._value)

    def __html__(self) -> str:
        return self._value


def mark_safe(value: str) -> SafeString:
    """Mark the safe."""
    return SafeString(value)


def escape(value: Any, autoescape: bool = True) -> str:
    """Perform the escape operation for this subsystem."""
    if value is None:
        return ""
    if isinstance(value, SafeString):
        return str(value)
    if not autoescape:
        return str(value)
    return Escaper.escape_html(str(value))
