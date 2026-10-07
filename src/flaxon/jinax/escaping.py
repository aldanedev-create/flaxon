from __future__ import annotations

import re
from typing import Any


class Escaper:
    HTML_ESCAPE = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }

    HTML_UNESCAPE = {v: k for k, v in HTML_ESCAPE.items()}

    @classmethod
    def escape_html(cls, value: str) -> str:
        if not value:
            return value
        return "".join(cls.HTML_ESCAPE.get(c, c) for c in value)

    @classmethod
    def unescape_html(cls, value: str) -> str:
        if not value:
            return value
        for escaped, original in cls.HTML_UNESCAPE.items():
            value = value.replace(escaped, original)
        return value

    @classmethod
    def escape_js(cls, value: str) -> str:
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
        if not value:
            return value
        # Terminate hex escapes so a following hex digit cannot extend them.
        return re.sub(r"[^a-zA-Z0-9]", lambda m: f"\\{ord(m.group(0)):x} ", value)

    @classmethod
    def escape_url(cls, value: str) -> str:
        import urllib.parse
        return urllib.parse.quote(value, safe="")

    @classmethod
    def unescape_url(cls, value: str) -> str:
        import urllib.parse
        return urllib.parse.unquote(value)

    @classmethod
    def escape_xml(cls, value: str) -> str:
        return cls.escape_html(value)

    @classmethod
    def escape_attribute(cls, value: str) -> str:
        return cls.escape_html(value)


class SafeString:
    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"SafeString({self._value!r})"

    def __add__(self, other: Any) -> SafeString:
        if isinstance(other, SafeString):
            return SafeString(self._value + other._value)
        return SafeString(self._value + str(other))

    def __radd__(self, other: Any) -> SafeString:
        return SafeString(str(other) + self._value)

    def __html__(self) -> str:
        return self._value


def mark_safe(value: str) -> SafeString:
    return SafeString(value)


def escape(value: Any, autoescape: bool = True) -> str:
    if value is None:
        return ""
    if isinstance(value, SafeString):
        return str(value)
    if not autoescape:
        return str(value)
    return Escaper.escape_html(str(value))
