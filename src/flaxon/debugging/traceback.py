from __future__ import annotations

import linecache
import traceback
from typing import Any


class TracebackFormatter:
    """Traceback formatter implementation for the debugging subsystem."""

    def __init__(self) -> None:
        self._max_frames = 20

    def format(self, exc: Exception) -> str:
        """Perform the format operation for traceback formatter."""
        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    def format_frames(self, exc: Exception) -> list[dict[str, Any]]:
        """Format the frames."""
        frames = []
        tb = exc.__traceback__

        while tb and len(frames) < self._max_frames:
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            lineno = tb.tb_lineno
            function = frame.f_code.co_name

            source_lines = self._get_source_lines(filename, lineno)

            frames.append({
                "filename": filename,
                "lineno": lineno,
                "function": function,
                "source": source_lines,
                "locals": self._get_locals(frame),
            })

            tb = tb.tb_next

        return frames

    def _get_source_lines(self, filename: str, lineno: int) -> list[str]:
        lines = []
        for i in range(max(0, lineno - 3), lineno + 2):
            line = linecache.getline(filename, i)
            if line:
                lines.append({
                    "number": i,
                    "text": line.rstrip("\n"),
                    "highlight": i == lineno,
                })
        return lines

    def _get_locals(self, frame: Any) -> dict[str, str]:
        locals_dict = {}
        for key, value in frame.f_locals.items():
            try:
                locals_dict[key] = repr(value)[:100]
            except Exception:
                locals_dict[key] = "<unable to display>"
        return locals_dict

    def format_simple(self, exc: Exception) -> str:
        """Format the simple."""
        return f"{type(exc).__name__}: {exc!s}"

    def get_summary(self, exc: Exception) -> dict[str, Any]:
        """Return the summary."""
        tb = exc.__traceback__
        last_frame = None

        while tb:
            last_frame = tb.tb_frame
            tb = tb.tb_next

        return {
            "type": type(exc).__name__,
            "message": str(exc),
            "filename": last_frame.f_code.co_filename if last_frame else None,
            "lineno": last_frame.f_lineno if last_frame else None,
            "function": last_frame.f_code.co_name if last_frame else None,
        }
