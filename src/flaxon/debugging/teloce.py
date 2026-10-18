"""Development-only ingestion of bounded, untrusted Teloce browser diagnostics."""

from __future__ import annotations

import hmac
import json
import re
import secrets
import time
import uuid
from typing import Any
from urllib.parse import unquote, urlsplit

from flaxon.debugging.redaction import Redactor
from flaxon.debugging.source_maps import source_position
from flaxon.exceptions import BadRequest, HTTPException
from flaxon.http import JSONResponse, Request

#: 403 codes the browser client uses to tell the two causes apart. Reloading fixes a stale
#: token (the server restarted) but can never fix a rejected origin.
ORIGIN_REJECTED = "FX-DEBUG-ORIGIN"
TOKEN_REJECTED = "FX-DEBUG-TOKEN"


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
        except (ValueError, UnicodeDecodeError, RecursionError) as error:
            raise BadRequest("Invalid diagnostic JSON") from error
        if not isinstance(report, dict):
            raise BadRequest("Diagnostic must be an object")
        result = self.record(report, client_reported=True)
        payload: dict[str, Any] = {
            "error_id": result["error_id"],
            "related_error_id": result.get("related_error_id"),
            "location": result.get("location"),
            "source_excerpt": result.get("source_excerpt"),
        }
        editor_url = self._editor_url(result)
        if editor_url:
            payload["editor_url"] = editor_url
        return JSONResponse(payload, headers={"cache-control": "no-store"})

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
        scheme = request.scope.get("scheme", "http")
        host = request.headers.get("host", "")
        try:
            origin = urlsplit(request.headers.get("origin", ""))
        except ValueError as error:
            raise HTTPException(403, "Invalid diagnostic origin", code=ORIGIN_REJECTED) from error
        if origin.netloc != host or origin.scheme != scheme:
            sent = f"{origin.scheme}://{origin.netloc}" if origin.netloc else "no Origin"
            raise HTTPException(
                403,
                "Development diagnostics require the same origin. "
                f"The browser sent {sent[:200]} but the server sees {scheme}://{host[:200]}. "
                "Behind a proxy or tunnel, make it send X-Forwarded-Proto and X-Forwarded-Host, "
                "and start the server with --forwarded-allow-ips (or FORWARDED_ALLOW_IPS) "
                "so Flaxon trusts it.",
                code=ORIGIN_REJECTED,
            )
        supplied = request.headers.get("x-flaxon-debug-token", "")
        if not hmac.compare_digest(supplied, self.token):
            raise HTTPException(403, "Invalid development diagnostic token", code=TOKEN_REJECTED)
        length = request.headers.get("content-length", "0")
        if len(length) > 5 or not length.isdecimal() or int(length) > 32768:
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
        allowed = {"compile", "ssr", "runtime", "hydration", "browser", "api", "typecheck"}
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
            # The mapped position is the answer even when the excerpt below is
            # refused (huge file, unreadable file): never drop it.
            error["location"] = f"{location['component']}:{location['line']}:{location['column']}"
        self._source_excerpt(error, location or report)
        self.integration.app.error_store.store(error)
        return error

    @staticmethod
    def _location_parts(location: Any) -> tuple[str, int, int] | None:
        """Split a stored `component:line:column` location back into its parts."""
        match = re.match(r"^(?P<path>.+):(?P<line>\d+):(?P<column>\d+)$", str(location or ""))
        return (match["path"], int(match["line"]), int(match["column"])) if match else None

    def _editor_url(self, error: dict[str, Any]) -> str | None:
        """Offer an editor link in debug mode, and only for a registered source file."""
        if not self.integration.app.debug:
            return None
        parts = self._location_parts(error.get("location"))
        if parts is None:
            return None
        component, line, column = parts
        try:
            path = (self.integration.project_root / component).resolve()
        except (OSError, ValueError):
            return None
        if not any(path.is_relative_to(source.directory) for source in self.integration.sources):
            return None
        return self.integration.editor_link.url_for(path, relpath=component, line=line, column=column)

    @staticmethod
    def _safe_path(value: Any) -> str:
        """Keep only a bounded page path, even when a report supplies a malformed URL."""
        try:
            return urlsplit(str(value)[:1000]).path
        except ValueError:
            return "/"

    def _known_output(self, path: str) -> str | None:
        """Resolve a reported build URL path to a known output, decoding percent escapes.

        Browsers percent-encode the path of a compiled component, so ``[id].js``
        arrives as ``%5Bid%5D.js`` and has to be decoded before it can be matched.
        The decoded path must still equal a known output *exactly*, which is what
        keeps ``..%2f`` from escaping: no build output contains a ``..`` segment,
        so a traversal never matches and no file outside the build is reachable.
        """
        prefix = self.integration.static_url + "/"
        output = unquote(path[len(prefix) :]) if path.startswith(prefix) else ""
        known = {item.get("output") for item in (self.integration.build_result or {}).get("files", [])}
        return output if output in known else None

    def _stack_position(self, report: dict[str, Any]) -> dict[str, Any]:
        if report.get("filename"):
            return report
        for match in re.finditer(r"(https?://[^\s()]+):(\d+):(\d+)", str(report.get("stack", ""))[:12000]):
            if self._known_output(self._safe_path(match[1])) is not None:
                return {**report, "filename": match[1], "line": match[2], "column": match[3]}
        return report

    def _map_browser_location(self, report: dict[str, Any]) -> dict[str, Any] | None:
        if not report.get("filename"):
            return None
        try:
            url = urlsplit(str(report["filename"])[:2000])
        except ValueError:
            return None
        output = self._known_output(url.path)
        if output is None:
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
            # A mapped location wins; without one this is still the best answer
            # for reports that name a component directly (SSR, typecheck).
            error.setdefault("location", f"{component}:{line}:{column}")
            error["source_excerpt"] = self.redactor.redact(
                "\n".join(
                    f"{index + 1}: {lines[index]}"
                    for index in range(max(0, line - 3), min(len(lines), line + 2))
                )
            )
        except (OSError, ValueError, TypeError):
            return
