from __future__ import annotations

import time
from typing import Any

from flaxon.http import HTMLResponse


class Dashboard:
    def __init__(self, error_store: Any, debug: bool = False) -> None:
        self.error_store = error_store
        self.debug = debug

    def render(self) -> HTMLResponse:
        stats = self.error_store.get_stats() if self.error_store else {}
        recent = self.error_store.get_recent(10) if self.error_store else []

        html = self._build_html(stats, recent)
        return HTMLResponse(html, status_code=200)

    def _build_html(self, stats: dict[str, Any], recent: list[dict[str, Any]]) -> str:
        import json

        stats_json = json.dumps(stats, indent=2, default=str)

        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Flaxon Debug Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #7dd3fc; font-size: 2rem; margin-bottom: 0.5rem; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 2rem; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }}
        .card h2 {{ color: #94a3b8; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
        .card .value {{ font-size: 2rem; font-weight: 700; color: #e2e8f0; }}
        .card .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }}
        .badge-success {{ background: #065f46; color: #6ee7b7; }}
        .badge-warning {{ background: #78350f; color: #fcd34d; }}
        .badge-danger {{ background: #7f1d1d; color: #fca5a5; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; padding: 0.75rem; color: #94a3b8; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid #334155; }}
        td {{ padding: 0.75rem; border-bottom: 1px solid #1e293b; }}
        .timestamp {{ color: #94a3b8; font-size: 0.875rem; }}
        .pre-wrap {{ white-space: pre-wrap; font-family: ui-monospace, monospace; font-size: 0.875rem; background: #0f172a; padding: 1rem; border-radius: 8px; margin-top: 0.5rem; overflow-x: auto; }}
        .flex {{ display: flex; justify-content: space-between; align-items: center; }}
        .mt-2 {{ margin-top: 0.5rem; }}
        .mb-2 {{ margin-bottom: 0.5rem; }}
        .text-muted {{ color: #94a3b8; }}
    </style>
</head>
<body>
<div class="container">
    <div class="flex">
        <div>
            <h1>Flaxon Debug Dashboard</h1>
            <p class="subtitle">Error monitoring and debugging interface</p>
        </div>
        <span class="badge badge-success">Debug Mode: {"Enabled" if self.debug else "Disabled"}</span>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Total Errors</h2>
            <div class="value">{stats.get("total", 0)}</div>
        </div>
        <div class="card">
            <h2>Error Types</h2>
            <div class="value">{len(stats.get("by_type", {}))}</div>
            <div class="mt-2 text-muted" style="font-size:0.875rem;">
                {", ".join(list(stats.get("by_type", {}).keys())[:3]) if stats.get("by_type") else "None"}
            </div>
        </div>
        <div class="card">
            <h2>Status</h2>
            <div class="value" style="color: {"#6ee7b7" if stats.get("total", 0) < 10 else "#fcd34d" if stats.get("total", 0) < 50 else "#fca5a5"};">
                {"Healthy" if stats.get("total", 0) < 10 else "Warning" if stats.get("total", 0) < 50 else "Critical"}
            </div>
        </div>
    </div>

    <div class="card" style="margin-bottom: 2rem;">
        <h2>Recent Errors</h2>
        {self._build_recent_table(recent)}
    </div>

    <div class="card">
        <h2>Statistics (JSON)</h2>
        <div class="pre-wrap">{stats_json}</div>
    </div>
</div>
</body>
</html>"""

    def _build_recent_table(self, recent: list[dict[str, Any]]) -> str:
        if not recent:
            return '<p class="text-muted" style="padding: 1rem;">No errors recorded.</p>'

        rows = ""
        for error in recent:
            error_type = error.get("type", "Unknown")
            path = error.get("path", "/")
            timestamp = error.get("timestamp", time.time())
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            rows += f"""
            <tr>
                <td><span class="badge badge-danger">{error_type}</span></td>
                <td>{path}</td>
                <td class="timestamp">{dt}</td>
                <td><code style="font-size:0.75rem; color:#94a3b8;">{error.get("error_id", "")[:8]}</code></td>
            </tr>
            """

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
