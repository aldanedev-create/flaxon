from __future__ import annotations

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
    def __init__(self, *, debug: bool = False) -> None:
        self.debug = debug
        self.error_codes = ErrorCodes()
        self.redactor = Redactor()
        self.formatter = Formatter()
        self.traceback_formatter = TracebackFormatter()

    async def response_for(self, exc: Exception, request: Any | None, scope: dict[str, Any]) -> Response:
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
        import html

        escaped_trace = html.escape(str(details["traceback"]))
        escaped_message = html.escape(str(details["message"]))

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Flaxon Debugger</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:2rem}}
main{{max-width:1100px;margin:auto}} .card{{background:#111827;border:1px solid #334155;border-radius:14px;padding:1.25rem;margin:1rem 0}}
h1{{color:#7dd3fc}} code,pre{{font-family:ui-monospace,monospace}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#020617;padding:1rem;border-radius:10px}}
.badge{{display:inline-block;background:#7f1d1d;padding:.25rem .5rem;border-radius:6px}}
</style></head><body><main>
<p class="badge">FX-DEV-500</p><h1>{html.escape(str(details["type"]))}: {escaped_message}</h1>
<div class="card"><strong>Request</strong><p>{html.escape(str(details["method"]))} {html.escape(str(details["path"]))}</p>
<p>Request ID: <code>{html.escape(str(details["request_id"]))}</code></p></div>
<div class="card"><strong>Traceback</strong><pre>{escaped_trace}</pre></div>
<p>This page is shown only because debug mode is enabled.</p>
</main></body></html>"""
