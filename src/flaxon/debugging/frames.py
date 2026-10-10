from __future__ import annotations

import linecache
from types import FrameType
from typing import Any


class FrameInfo:
    """Frame info implementation for the debugging subsystem."""

    def __init__(self, frame: FrameType) -> None:
        self.frame = frame
        self.filename = frame.f_code.co_filename
        self.lineno = frame.f_lineno
        self.function = frame.f_code.co_name
        self.locals = self._capture_locals()
        self.globals = self._capture_globals()

    def _capture_locals(self) -> dict[str, Any]:
        result = {}
        for key, value in self.frame.f_locals.items():
            try:
                result[key] = repr(value)[:200]
            except Exception:
                result[key] = "<unable to display>"
        return result

    def _capture_globals(self) -> dict[str, Any]:
        result = {}
        for key, value in self.frame.f_globals.items():
            if not key.startswith("__"):
                try:
                    result[key] = repr(value)[:100]
                except Exception:
                    result[key] = "<unable to display>"
        return result

    def get_source_lines(self, context: int = 5) -> list[dict[str, Any]]:
        """Return the source lines."""
        lines = []
        for i in range(max(0, self.lineno - context), self.lineno + context + 1):
            line = linecache.getline(self.filename, i)
            if line:
                lines.append({
                    "number": i,
                    "text": line.rstrip("\n"),
                    "highlight": i == self.lineno,
                })
        return lines

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "filename": self.filename,
            "lineno": self.lineno,
            "function": self.function,
            "locals": self.locals,
            "source": self.get_source_lines(),
        }


class FrameStack:
    """Frame stack implementation for the debugging subsystem."""

    def __init__(self, exc: Exception) -> None:
        self.frames = []
        tb = exc.__traceback__

        while tb:
            self.frames.append(FrameInfo(tb.tb_frame))
            tb = tb.tb_next

    def to_dict(self) -> list[dict[str, Any]]:
        """Return a dictionary representation of the current value."""
        return [frame.to_dict() for frame in self.frames]

    def get_current_frame(self) -> FrameInfo | None:
        """Return the current frame."""
        return self.frames[-1] if self.frames else None

    def get_first_frame(self) -> FrameInfo | None:
        """Return the first frame."""
        return self.frames[0] if self.frames else None

    def get_frames_before(self, count: int = 10) -> list[FrameInfo]:
        """Return the frames before."""
        return self.frames[-count:]

    def get_frames_after(self, count: int = 10) -> list[FrameInfo]:
        """Return the frames after."""
        return self.frames[:count]

    def __len__(self) -> int:
        return len(self.frames)

    def __iter__(self):
        return iter(self.frames)
