from __future__ import annotations

from typing import Any, ClassVar


class SecurityHeaders:
    """Security headers implementation for the security subsystem."""

    DEFAULT_POLICIES: ClassVar[Any] = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin",
        "permissions-policy": "geolocation=(), microphone=(), camera=()",
        "x-xss-protection": "1; mode=block",
    }

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        hsts: bool = False,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp: str | None = None,
        csp_report_only: bool = False,
        custom_headers: dict[str, str] | None = None,
    ) -> None:
        self.headers = {**self.DEFAULT_POLICIES, **(custom_headers or {})}

        if hsts:
            hsts_value = f"max-age={hsts_max_age}"
            if hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if hsts_preload:
                hsts_value += "; preload"
            self.headers["strict-transport-security"] = hsts_value

        if csp:
            header_name = "content-security-policy"
            if csp_report_only:
                header_name = "content-security-policy-report-only"
            self.headers[header_name] = csp

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """Perform the apply operation for security headers."""
        result = dict(headers)
        for key, value in self.headers.items():
            if key not in result:
                result[key] = value
        return result

    def apply_to_response(self, response: Any) -> None:
        """Apply the to response."""
        for key, value in self.headers.items():
            if key not in response.headers:
                response.headers[key] = value


def add_security_headers(headers: dict[str, str]) -> dict[str, str]:
    """Add the security headers."""
    security = SecurityHeaders()
    return security.apply(headers)
