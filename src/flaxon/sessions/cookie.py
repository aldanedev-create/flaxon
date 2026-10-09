
from __future__ import annotations

from datetime import datetime


class CookieSession:
    def __init__(
        self,
        name: str,
        value: str,
        max_age: int | None = None,
        expires: datetime | None = None,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool = True,
        httponly: bool = True,
        samesite: str = "lax",
    ) -> None:
        self.name = name
        self.value = value
        self.max_age = max_age
        self.expires = expires
        self.path = path
        self.domain = domain
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite

    def to_header(self) -> str:
        parts = [f"{self.name}={self.value}"]

        if self.max_age is not None:
            parts.append(f"Max-Age={self.max_age}")

        if self.expires:
            parts.append(f"Expires={self.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')}")

        if self.path:
            parts.append(f"Path={self.path}")

        if self.domain:
            parts.append(f"Domain={self.domain}")

        if self.secure:
            parts.append("Secure")

        if self.httponly:
            parts.append("HttpOnly")

        if self.samesite:
            parts.append(f"SameSite={self.samesite.capitalize()}")

        return "; ".join(parts)


class CookieManager:
    def __init__(
        self,
        cookie_name: str = "session",
        cookie_path: str = "/",
        cookie_domain: str | None = None,
        cookie_secure: bool = True,
        cookie_httponly: bool = True,
        cookie_samesite: str = "lax",
    ) -> None:
        self.cookie_name = cookie_name
        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite

    def create_cookie(self, value: str, max_age: int) -> str:
        cookie = CookieSession(
            name=self.cookie_name,
            value=value,
            max_age=max_age,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
        return cookie.to_header()

    def delete_cookie(self) -> str:
        cookie = CookieSession(
            name=self.cookie_name,
            value="",
            max_age=0,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
        return cookie.to_header()

    def parse_cookies(self, cookie_header: str) -> dict[str, str]:
        cookies = {}
        if not cookie_header:
            return cookies

        for item in cookie_header.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookies[key.strip()] = value.strip()

        return cookies

    def get_cookie_value(self, cookie_header: str, name: str | None = None) -> str | None:
        name = name or self.cookie_name
        cookies = self.parse_cookies(cookie_header)
        return cookies.get(name)
