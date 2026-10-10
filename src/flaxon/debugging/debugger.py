from __future__ import annotations

import html
import traceback
import uuid
from typing import Any

from flaxon.exceptions import HTTPException
from flaxon.http import HTMLResponse, JSONResponse, Response

from .error_codes import ErrorCodes
from .formatter import Formatter
from .redaction import Redactor
from .request_snapshot import RequestSnapshot
from .traceback import TracebackFormatter


class Debugger:
    """Debugger implementation for the debugging subsystem."""

    def __init__(self, *, debug: bool = False) -> None:
        self.debug = debug
        self.error_codes = ErrorCodes()
        self.redactor = Redactor()
        self.formatter = Formatter()
        self.traceback_formatter = TracebackFormatter()

    async def response_for(self, exc: Exception, request: Any | None, scope: dict[str, Any]) -> Response:
        """Perform the response for operation for debugger."""
        error_id = f"fx_{uuid.uuid4().hex[:12]}"
        request_id = scope.get("flaxon.request_id", error_id)

        if isinstance(exc, HTTPException):
            payload = {
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.detail,
                    "request_id": request_id,
                    **exc.extra,
                },
            }
            return JSONResponse(payload, status_code=exc.status_code, headers=exc.headers)

        if not self.debug:
            return JSONResponse(
                {
                    "success": False,
                    "error": {
                        "code": "FX-SRV-500",
                        "message": "The request could not be completed.",
                        "request_id": request_id,
                    },
                },
                status_code=500,
            )

        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        snapshot = RequestSnapshot.from_request(request) if request else None

        details = {
            "error_id": error_id,
            "request_id": request_id,
            "type": type(exc).__name__,
            "message": str(exc),
            "method": getattr(request, "method", scope.get("method")),
            "path": getattr(request, "path", scope.get("path")),
            "path_params": self.redactor.redact(getattr(request, "path_params", {})),
            "query": self.redactor.redact(getattr(request, "query", {})),
            "traceback": trace,
            "snapshot": snapshot.to_dict() if snapshot else None,
        }

        accept = ""
        if request is not None:
            accept = request.headers.get("accept", "")

        if "text/html" in accept:
            return HTMLResponse(self._html(details), status_code=500)

        return JSONResponse(
            {
                "success": False,
                "error": {
                    "code": "FX-DEV-500",
                    "message": str(exc),
                    "request_id": request_id,
                    "debug": details,
                },
            },
            status_code=500,
        )

    def _html(self, details: dict[str, Any]) -> str:

        escaped_trace = html.escape(str(details["traceback"]))
        escaped_message = html.escape(str(details["message"]))

        return (
            '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            "<title>Flaxon Debugger</title>\n<style>\nbody{font-family:syst"
            "em-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;p"
            "adding:2rem}\nmain{max-width:1100px;margin:auto} .card{backgr"
            "ound:#111827;border:1px solid #334155;border-radius:14px;pad"
            "ding:1.25rem;margin:1rem 0}\nh1{color:#7dd3fc} code,pre{font-"
            "family:ui-monospace,monospace} pre{white-space:pre-wrap;over"
            "flow-wrap:anywhere;background:#020617;padding:1rem;border-ra"
            "dius:10px}\n.badge{display:inline-block;background:#7f1d1d;pa"
            "dding:.25rem .5rem;border-radius:6px}\n</style></head><body><"
            'main>\n<p class="badge">FX-DEV-500</p><h1>'
            f"{html.escape(str(details['type']))}"
            ": "
            f"{escaped_message}"
            '</h1>\n<div class="card"><strong>Request</strong><p>'
            f"{html.escape(str(details['method']))}"
            " "
            f"{html.escape(str(details['path']))}"
            "</p>\n<p>Request ID: <code>"
            f"{html.escape(str(details['request_id']))}"
            '</code></p></div>\n<div class="card"><strong>Traceback</stron'
            "g><pre>"
            f"{escaped_trace}"
            "</pre></div>\n<p>This page is shown only because debug mode i"
            "s enabled.</p>\n</main></body></html>"
        )
