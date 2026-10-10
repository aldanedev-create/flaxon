"""Development-only ingestion of bounded, untrusted Teloce browser diagnostics."""

from __future__ import annotations

import hmac
import json
import re
import secrets
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

from flaxon.debugging.redaction import Redactor
from flaxon.debugging.source_maps import source_position
from flaxon.exceptions import BadRequest, Forbidden, HTTPException
from flaxon.http import JSONResponse, Request


class TeloceDebugger:
    """Join compiler, SSR and browser reports in the existing development error store."""

    def __init__(self, integration: Any) -> None:
        self.integration = integration
        self.token = secrets.token_urlsafe(32)
        self._window = time.monotonic()
        self._reports = 0
        self.redactor = Redactor()
        if integration.app.debug:
            integration.app.router.post("/__debug__/teloce/errors")(self.receive)

    async def receive(self, request: Request) -> JSONResponse:
        """Validate origin, token, size and rate before accepting a browser report."""
        self._authorize(request)
        raw = await self._bounded_body(request)
        if len(raw) > 32768:
            raise BadRequest("Browser diagnostic is too large")
        try:
            report = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as error:
            raise BadRequest("Invalid diagnostic JSON") from error
        if not isinstance(report, dict):
            raise BadRequest("Diagnostic must be an object")
        result = self.record(report, client_reported=True)
        return JSONResponse(
            {
                "error_id": result["error_id"],
                "related_error_id": result.get("related_error_id"),
                "location": result.get("location"),
                "source_excerpt": result.get("source_excerpt"),
            },
            headers={"cache-control": "no-store"},
        )

    async def _bounded_body(self, request: Request) -> bytes:
        """Reject an oversized body while receiving it, including chunked transport."""
        parts = []
        size = 0
        while True:
            frame = await request._receive()
            if frame.get("type") != "http.request":
                break
            chunk = frame.get("body", b"")
            size += len(chunk)
            if size > 32768:
                raise BadRequest("Browser diagnostic is too large")
            parts.append(chunk)
            if not frame.get("more_body", False):
                break
        return b"".join(parts)

    def _authorize(self, request: Request) -> None:
        if not self.integration.app.debug:
            raise HTTPException(404, "Not found")
        try:
            origin = urlsplit(request.headers.get("origin", ""))
        except ValueError as error:
            raise Forbidden("Invalid diagnostic origin") from error
        if origin.netloc != request.headers.get("host", "") or origin.scheme != request.scope.get(
            "scheme", "http"
        ):
            raise Forbidden("Development diagnostics require the same origin")
        supplied = request.headers.get("x-flaxon-debug-token", "")
        if not hmac.compare_digest(supplied, self.token):
            raise Forbidden("Invalid development diagnostic token")
        length = request.headers.get("content-length", "0")
        if not length.isdecimal() or int(length) > 32768:
            raise BadRequest("Browser diagnostic is too large")
        now = time.monotonic()
        if now - self._window > 60:
            self._window, self._reports = now, 0
        self._reports += 1
        if self._reports > 120:
            raise HTTPException(429, "Too many browser diagnostics")

    def record(self, report: dict[str, Any], *, client_reported: bool = False) -> dict[str, Any]:
        """Store a sanitized report; resolve source only through registered build inputs."""
        category = str(report.get("category", "runtime"))[:32]
        allowed = {"compile", "ssr", "runtime", "hydration", "browser", "api"}
        if category not in allowed:
            category = "browser"
        error: dict[str, Any] = {
            "error_id": str(uuid.uuid4()),
            "type": f"Teloce {category}",
            "timestamp": time.time(),
            "message": self.redactor.redact(
                self.redactor.redact_url(str(report.get("message", "Unknown error"))[:4000])
            ),
            "stack": self.redactor.redact(self.redactor.redact_url(str(report.get("stack", ""))[:12000])),
            "path": self._safe_path(report.get("path", "/")),
            "component": str(report.get("component", ""))[:500],
            "request_id": str(report.get("request_id", ""))[:128],
            "client_reported": client_reported,
        }
        related = next(
            (
                item
                for item in reversed(self.integration.app.error_store.get_recent(1000))
                if error["request_id"]
                and item.get("request_id") == error["request_id"]
                and not item.get("client_reported")
            ),
            None,
        )
        if related and not related.get("client_reported"):
            error["related_error_id"] = related["error_id"]
        mapped_report = self._stack_position(report)
        location = self._map_browser_location(mapped_report)
        if location:
            error["component"] = location["component"]
        self._source_excerpt(error, location or report)
        self.integration.app.error_store.store(error)
        return error

    @staticmethod
    def _safe_path(value: Any) -> str:
        """Keep only a bounded page path, even when a report supplies a malformed URL."""
        try:
            return urlsplit(str(value)[:1000]).path
        except ValueError:
            return "/"

    def _stack_position(self, report: dict[str, Any]) -> dict[str, Any]:
        if report.get("filename"):
            return report
        known = {item.get("output") for item in (self.integration.build_result or {}).get("files", [])}
        prefix = self.integration.static_url + "/"
        for match in re.finditer(r"(https?://[^\s()]+):(\d+):(\d+)", str(report.get("stack", ""))[:12000]):
            url = self._safe_path(match[1])
            if url.startswith(prefix) and url[len(prefix) :] in known:
                return {**report, "filename": match[1], "line": match[2], "column": match[3]}
        return report

    def _map_browser_location(self, report: dict[str, Any]) -> dict[str, Any] | None:
        if not report.get("filename"):
            return None
        try:
            url = urlsplit(str(report["filename"])[:2000])
        except ValueError:
            return None
        prefix = self.integration.static_url + "/"
        output = url.path[len(prefix) :] if url.path.startswith(prefix) else ""
        known = {item.get("output") for item in (self.integration.build_result or {}).get("files", [])}
        if output not in known:
            return None
        try:
            path = (self.integration.build_dir / (output + ".map")).resolve()
            path.relative_to(self.integration.build_dir)
            if path.stat().st_size > 2_000_000:
                return None
            mapping = json.loads(path.read_text(encoding="utf-8"))
            position = source_position(mapping, int(report.get("line", 1)), int(report.get("column", 1)))
            return (
                {"component": position[0], "line": position[1], "column": position[2]} if position else None
            )
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def _source_excerpt(self, error: dict[str, Any], report: dict[str, Any]) -> None:
        result = self.integration.build_result or {}
        allowed = {item.get("input") for item in result.get("files", [])}
        component = error["component"]
        if component not in allowed or not component.endswith((".html", ".vel", ".ts")):
            return
        try:
            line = max(1, int(report.get("line", 1)))
            column = max(1, int(report.get("column", 1)))
            path = (self.integration.project_root / component).resolve()
            if not any(path.is_relative_to(source.directory) for source in self.integration.sources):
                return
            if path.stat().st_size > 200000:
                return
            lines = path.read_text(encoding="utf-8").splitlines()
            error["location"] = f"{component}:{line}:{column}"
            error["source_excerpt"] = self.redactor.redact(
                "\n".join(
                    f"{index + 1}: {lines[index]}"
                    for index in range(max(0, line - 3), min(len(lines), line + 2))
                )
            )
        except (OSError, ValueError, TypeError):
            return
