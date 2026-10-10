from __future__ import annotations

import json
import time
from html import escape
from typing import Any

from flaxon.http import HTMLResponse


class Dashboard:
    """Dashboard implementation for the debugging subsystem."""

    def __init__(self, error_store: Any, debug: bool = False) -> None:
        self.error_store = error_store
        self.debug = debug

    def render(self) -> HTMLResponse:
        """Render the requested content using the supplied context."""
        stats = self.error_store.get_stats() if self.error_store else {}
        recent = self.error_store.get_recent(10) if self.error_store else []

        html = self._build_html(stats, recent)
        return HTMLResponse(html, status_code=200)

    def _build_html(self, stats: dict[str, Any], recent: list[dict[str, Any]]) -> str:

        stats_json = escape(json.dumps(stats, indent=2, default=str))

        error_types = escape(
            ", ".join(list(stats.get("by_type", {}).keys())[:3]) if stats.get("by_type") else "None"
        )
        total = stats.get("total", 0)
        status_color, status_label = (
            ("#6ee7b7", "Healthy")
            if total < 10
            else ("#fcd34d", "Warning")
            if total < 50
            else ("#fca5a5", "Critical")
        )
        return (
            '<!doctype html>\n<html lang="en">\n<head>\n    <meta charset="u'
            'tf-8">\n    <meta name="viewport" content="width=device-width'
            ', initial-scale=1">\n    <title>Flaxon Debug Dashboard</title'
            ">\n    <style>\n        * { margin: 0; padding: 0; box-sizing:"
            " border-box; }\n        body { font-family: system-ui, sans-s"
            "erif; background: #0f172a; color: #e2e8f0; padding: 2rem; }\n"
            "        .container { max-width: 1200px; margin: 0 auto; }\n  "
            "      h1 { color: #7dd3fc; font-size: 2rem; margin-bottom: 0"
            ".5rem; }\n        .subtitle { color: #94a3b8; margin-bottom: "
            "2rem; }\n        .grid { display: grid; grid-template-columns"
            ": repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-"
            "bottom: 2rem; }\n        .card { background: #1e293b; border-"
            "radius: 12px; padding: 1.5rem; border: 1px solid #334155; }\n"
            "        .card h2 { color: #94a3b8; font-size: 0.875rem; text"
            "-transform: uppercase; letter-spacing: 0.05em; margin-bottom"
            ": 0.5rem; }\n        .card .value { font-size: 2rem; font-wei"
            "ght: 700; color: #e2e8f0; }\n        .card .badge { display: "
            "inline-block; padding: 0.25rem 0.75rem; border-radius: 9999p"
            "x; font-size: 0.75rem; font-weight: 600; }\n        .badge-su"
            "ccess { background: #065f46; color: #6ee7b7; }\n        .badg"
            "e-warning { background: #78350f; color: #fcd34d; }\n        ."
            "badge-danger { background: #7f1d1d; color: #fca5a5; }\n      "
            "  table { width: 100%; border-collapse: collapse; }\n        "
            "th { text-align: left; padding: 0.75rem; color: #94a3b8; fon"
            "t-weight: 600; font-size: 0.75rem; text-transform: uppercase"
            "; border-bottom: 1px solid #334155; }\n        td { padding: "
            "0.75rem; border-bottom: 1px solid #1e293b; }\n        .timest"
            "amp { color: #94a3b8; font-size: 0.875rem; }\n        .pre-wr"
            "ap { white-space: pre-wrap; font-family: ui-monospace, monos"
            "pace; font-size: 0.875rem; background: #0f172a; padding: 1re"
            "m; border-radius: 8px; margin-top: 0.5rem; overflow-x: auto;"
            " }\n        .flex { display: flex; justify-content: space-bet"
            "ween; align-items: center; }\n        .mt-2 { margin-top: 0.5"
            "rem; }\n        .mb-2 { margin-bottom: 0.5rem; }\n        .tex"
            "t-muted { color: #94a3b8; }\n    </style>\n</head>\n<body>\n<div"
            ' class="container">\n    <div class="flex">\n        <div>\n   '
            "         <h1>Flaxon Debug Dashboard</h1>\n            <p clas"
            's="subtitle">Error monitoring and debugging interface</p>\n  '
            '      </div>\n        <span class="badge badge-success">Debug'
            " Mode: "
            f"{('Enabled' if self.debug else 'Disabled')}"
            '</span>\n    </div>\n\n    <div class="grid">\n        <div clas'
            's="card">\n            <h2>Total Errors</h2>\n            <div'
            ' class="value">'
            f"{stats.get('total', 0)}"
            '</div>\n        </div>\n        <div class="card">\n           '
            ' <h2>Error Types</h2>\n            <div class="value">'
            f"{len(stats.get('by_type', {}))}"
            '</div>\n            <div class="mt-2 text-muted" style="font-'
            'size:0.875rem;">\n                '
            f"{error_types}"
            '\n            </div>\n        </div>\n        <div class="card"'
            '>\n            <h2>Status</h2>\n            <div class="value"'
            ' style="color: '
            f"{status_color}"
            ';">\n                '
            f"{status_label}"
            "\n            </div>\n        </div>\n    </div>\n\n    <div clas"
            's="card" style="margin-bottom: 2rem;">\n        <h2>Recent Er'
            "rors</h2>\n        "
            f"{self._build_recent_table(recent)}"
            '\n    </div>\n\n    <div class="card">\n        <h2>Statistics ('
            'JSON)</h2>\n        <div class="pre-wrap">'
            f"{stats_json}"
            "</div>\n    </div>\n</div>\n</body>\n</html>"
        )

    def _build_recent_table(self, recent: list[dict[str, Any]]) -> str:
        if not recent:
            return '<p class="text-muted" style="padding: 1rem;">No errors recorded.</p>'

        rows = ""
        for error in recent:
            error_type = escape(str(error.get("type", "Unknown")))
            path = escape(str(error.get("path", "/")))
            timestamp = error.get("timestamp", time.time())
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            rows += (
                f'\n            <tr id="error-{escape(str(error.get("error_id", "")), quote=True)}">\n'
                '                <td><span class="badge bad'
                'ge-danger">'
                f"{error_type}"
                "</span></td>\n                <td>"
                f"{path}"
                '</td>\n                <td class="timestamp">'
                f"{dt}"
                '</td>\n                <td><code style="font-size:0.75rem; co'
                'lor:#94a3b8;">'
                f"{escape(str(error.get('error_id', ''))[:8])}"
                "</code><details><summary>"
                f"{escape(str(error.get('message', 'Details')))}"
                "</summary><pre>"
                f"Related server error: {escape(str(error.get('related_error_id', '')))}\n"
                f"{escape(str(error.get('location', '')))}\n"
                f"{escape(str(error.get('source_excerpt', '')))}\n"
                f"{escape(str(error.get('stack', '')))}"
                "</pre></details></td>\n            </tr>\n            "
            )

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Path</th>
                    <th>Time</th>
                    <th>ID</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
