from __future__ import annotations

import html
import re
from typing import Any


class Sanitizer:
    @staticmethod
    def allow_html(value: str, tags: set[str] | None = None, attributes: set[str] | None = None) -> str:
        """Keep a conservative formatting allowlist and remove active attributes.

        ``nh3`` is used when installed because it parses HTML rather than
        relying on regular expressions. The small fallback keeps Flaxon
        usable without optional dependencies, but production deployments
        should install ``flaxon[admin]``.
        """
        tags = tags or {"p", "br", "strong", "em", "b", "i", "u", "ul", "ol", "li", "blockquote", "a"}
        attributes = attributes or {"href", "title"}
        try:
            import nh3
        except ImportError:
            nh3 = None
        if nh3 is not None:
            allowed_attributes = {tag: set(attributes) for tag in tags}
            # Keep the historical Flaxon behavior of removing active markup
            # while retaining its text content (``<script>bad()</script>``
            # becomes ``bad()``), which is useful for editorial previews.
            value = re.sub(r"</?\s*(script|style|iframe|object|embed)\b[^>]*>", "", str(value), flags=re.IGNORECASE)
            try:
                return nh3.clean(
                    str(value),
                    tags=set(tags),
                    attributes=allowed_attributes,
                    url_schemes={"http", "https", "mailto"},
                )
            except TypeError:
                # Older nh3 releases expose the same sanitizer with a
                # narrower keyword signature. Keep the allowlist explicit.
                return nh3.clean(str(value), tags=set(tags), attributes=allowed_attributes)

        def clean_tag(match: re.Match[str]) -> str:
            closing, name, raw_attrs = match.group(1), match.group(2).lower(), match.group(3) or ""
            if name not in tags:
                return ""
            if closing:
                return f"</{name}>"
            safe = []
            for attr, quote, val in re.findall(r"([\w-]+)\s*=\s*(['\"])(.*?)\2", raw_attrs):
                if attr.lower() in attributes and not re.match(r"(?i)\s*(javascript|data):", val):
                    safe.append(f'{attr.lower()}="{html.escape(val, quote=True)}"')
            return f"<{name}{(' ' + ' '.join(safe)) if safe else ''}>"
        return re.sub(r"<\s*(/?)\s*([\w-]+)([^>]*)>", clean_tag, str(value))
    @staticmethod
    def html_escape(value: str) -> str:
        return html.escape(value)

    @staticmethod
    def html_unescape(value: str) -> str:
        return html.unescape(value)

    @staticmethod
    def strip_tags(value: str) -> str:
        # Remove executable/active element contents before stripping markup.
        value = re.sub(
            r"<(script|style|iframe|object|embed)\b[^>]*>.*?</\1\s*>",
            "",
            value,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return re.sub(r"<[^>]*>", "", value)

    @staticmethod
    def strip_whitespace(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def strip_control_chars(value: str) -> str:
        return re.sub(r"[\x00-\x1f\x7f]", "", value)

    @staticmethod
    def strip_sql(value: str) -> str:
        sql_keywords = [
            "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
            "ALTER", "TRUNCATE", "EXEC", "EXECUTE", "UNION", "JOIN",
            "WHERE", "HAVING", "GROUP BY", "ORDER BY", "LIMIT", "OFFSET",
        ]
        pattern = "|".join(rf"\b{kw}\b" for kw in sql_keywords)
        return re.sub(pattern, "", value, flags=re.IGNORECASE)

    @staticmethod
    def strip_path_traversal(value: str) -> str:
        return re.sub(r"\.\./", "", value)

    @staticmethod
    def sanitize_filename(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]", "_", value)

    @staticmethod
    def sanitize_email(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9@._-]", "", value)

    @staticmethod
    def sanitize_phone(value: str) -> str:
        return re.sub(r"[^0-9+()-]", "", value)

    @staticmethod
    def sanitize_url(value: str) -> str:
        return re.sub(r"[^\w\-.:/?%&=#]", "", value)


class InputSanitizer:
    def __init__(self, strip_tags: bool = False, html_escape: bool = True) -> None:
        self.strip_tags = strip_tags
        self.html_escape = html_escape

    def sanitize(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            if self.strip_tags:
                value = Sanitizer.strip_tags(value)
            if self.html_escape:
                value = Sanitizer.html_escape(value)
            return Sanitizer.strip_whitespace(value)
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, dict):
            return {key: self.sanitize(val) for key, val in value.items()}
        return value
