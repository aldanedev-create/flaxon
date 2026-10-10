from __future__ import annotations

import time
from typing import Any


class TemplateDiagnostics:
    """Template diagnostics implementation for the jinax subsystem."""

    def __init__(self) -> None:
        self._render_times: dict[str, list[float]] = {}
        self._errors: dict[str, list[str]] = {}
        self._cache_hits: dict[str, int] = {}
        self._cache_misses: dict[str, int] = {}

    def record_render(self, template_name: str, duration: float) -> None:
        """Record the render."""
        if template_name not in self._render_times:
            self._render_times[template_name] = []
        self._render_times[template_name].append(duration)

    def record_error(self, template_name: str, error: str) -> None:
        """Record the error."""
        if template_name not in self._errors:
            self._errors[template_name] = []
        self._errors[template_name].append(error)

    def record_cache_hit(self, template_name: str) -> None:
        """Record the cache hit."""
        self._cache_hits[template_name] = self._cache_hits.get(template_name, 0) + 1

    def record_cache_miss(self, template_name: str) -> None:
        """Record the cache miss."""
        self._cache_misses[template_name] = self._cache_misses.get(template_name, 0) + 1

    def get_stats(self, template_name: str) -> dict[str, Any]:
        """Return the stats."""
        times = self._render_times.get(template_name, [])
        errors = self._errors.get(template_name, [])
        hits = self._cache_hits.get(template_name, 0)
        misses = self._cache_misses.get(template_name, 0)

        return {
            "template": template_name,
            "render_count": len(times),
            "avg_render_time": sum(times) / len(times) if times else 0,
            "min_render_time": min(times) if times else 0,
            "max_render_time": max(times) if times else 0,
            "error_count": len(errors),
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_hit_rate": hits / (hits + misses) if (hits + misses) > 0 else 0,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Return the all stats."""
        return {name: self.get_stats(name) for name in self._render_times}

    def clear(self) -> None:
        """Remove the stored entries."""
        self._render_times.clear()
        self._errors.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()


class TemplateProfiler:
    """Template profiler implementation for the jinax subsystem."""

    def __init__(self) -> None:
        self._current_templates: list[str] = []
        self._start_times: list[float] = []

    def start(self, template_name: str) -> None:
        """Start the configured service."""
        self._current_templates.append(template_name)
        self._start_times.append(time.perf_counter())

    def end(self) -> float:
        """Perform the end operation for template profiler."""
        if not self._start_times:
            return 0
        start = self._start_times.pop()
        self._current_templates.pop()
        return (time.perf_counter() - start) * 1000

    def current_template(self) -> str | None:
        """Perform the current template operation for template profiler."""
        return self._current_templates[-1] if self._current_templates else None

    def depth(self) -> int:
        """Perform the depth operation for template profiler."""
        return len(self._current_templates)


class DiagnosticMiddleware:
    """Diagnostic middleware implementation for the jinax subsystem."""

    def __init__(self, app: Any, diagnostics: TemplateDiagnostics) -> None:
        self.app = app
        self.diagnostics = diagnostics

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
