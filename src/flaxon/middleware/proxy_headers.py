"""
Proxy headers middleware for Flaxon.

This module provides middleware for handling proxy headers like X-Forwarded-*.
"""

from __future__ import annotations

from typing import Any

from .base import Middleware


class ProxyHeadersMiddleware(Middleware):
    """Proxy headers middleware."""

    def __init__(
        self,
        app: Any,
        trusted_proxies: list[str] | tuple[str, ...] | None = None,
        forward_for: bool = True,
        forward_proto: bool = True,
        forward_host: bool = True,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = set(trusted_proxies or [])
        self.forward_for = forward_for
        self.forward_proto = forward_proto
        self.forward_host = forward_host

    def _is_trusted_proxy(self, ip: str) -> bool:
        if not self.trusted_proxies:
            return False

        if "*" in self.trusted_proxies:
            return True

        if ip in self.trusted_proxies:
            return True

        for cidr in self.trusted_proxies:
            if self._ip_in_cidr(ip, cidr):
                return True

        return False

    def _ip_in_cidr(self, ip: str, cidr: str) -> bool:
        try:
            import ipaddress
            return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
        except (ValueError, ImportError):
            return False

    def _get_client_ip(self, scope: dict[str, Any]) -> str | None:
        client = scope.get("client")
        if client:
            return client[0]
        return None

    def _get_header(self, scope: dict[str, Any], name: str) -> str | None:
        for key, value in scope.get("headers", []):
            if key.lower() == name.lower().encode("latin-1"):
                return value.decode("latin-1")
        return None

    def _get_forwarded_for(self, scope: dict[str, Any]) -> list[str]:
        header = self._get_header(scope, "x-forwarded-for")
        if not header:
            return []

        ips = [ip.strip() for ip in header.split(",") if ip.strip()]

        if not self.trusted_proxies:
            return ips

        result = []
        for ip in reversed(ips):
            if self._is_trusted_proxy(ip):
                continue
            result.append(ip)

        if not result and ips:
            result.append(ips[0])

        return result

    def _get_forwarded_proto(self, scope: dict[str, Any]) -> str | None:
        header = self._get_header(scope, "x-forwarded-proto")
        if header:
            return header.split(",")[0].strip()
        return None

    def _get_forwarded_host(self, scope: dict[str, Any]) -> str | None:
        header = self._get_header(scope, "x-forwarded-host")
        if header:
            return header.split(",")[0].strip()
        return None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        client_ip = self._get_client_ip(scope)
        if not client_ip or not self._is_trusted_proxy(client_ip):
            await self.app(scope, receive, send)
            return

        if self.forward_for:
            forwarded_for = self._get_forwarded_for(scope)
            if forwarded_for:
                scope["client"] = (forwarded_for[0], 0)
                scope["flaxon.forwarded_for"] = forwarded_for

        if self.forward_proto:
            proto = self._get_forwarded_proto(scope)
            if proto in {"http", "https"}:
                scope["scheme"] = proto
                scope["flaxon.forwarded_proto"] = proto

        if self.forward_host:
            host = self._get_forwarded_host(scope)
            if host:
                headers = list(scope.get("headers", []))
                found = False
                for i, (key, _) in enumerate(headers):
                    if key.lower() == b"host":
                        headers[i] = (b"host", host.encode("latin-1"))
                        found = True
                        break
                if not found:
                    headers.append((b"host", host.encode("latin-1")))
                scope["headers"] = headers
                scope["flaxon.forwarded_host"] = host

        await self.app(scope, receive, send)
