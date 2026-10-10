from __future__ import annotations

import inspect
import sys
from typing import Any


class Inspector:
    """Inspector implementation for the debugging subsystem."""

    def __init__(self) -> None:
        self._cached_imports: dict[str, Any] = {}

    def get_module_info(self, module_name: str) -> dict[str, Any]:
        """Return the module info."""
        try:
            module = sys.modules.get(module_name)
            if module is None:
                return {"name": module_name, "exists": False}

            return {
                "name": module_name,
                "exists": True,
                "file": getattr(module, "__file__", None),
                "doc": (module.__doc__ or "")[:200],
                "version": getattr(module, "__version__", None),
                "members": self.get_module_members(module),
            }
        except Exception:
            return {"name": module_name, "exists": False, "error": "Failed to inspect module"}

    def get_module_members(self, module: Any) -> list[str]:
        """Return the module members."""
        members = []
        for name in dir(module):
            if not name.startswith("_"):
                members.append(name)
        return members[:50]

    def get_object_info(self, obj: Any) -> dict[str, Any]:
        """Return the object info."""
        return {
            "type": type(obj).__name__,
            "module": getattr(obj, "__module__", None),
            "doc": (obj.__doc__ or "")[:200],
            "dir": [d for d in dir(obj) if not d.startswith("_")][:20],
        }

    def get_function_info(self, func: Any) -> dict[str, Any]:
        """Return the function info."""
        signature = inspect.signature(func)
        return {
            "name": getattr(func, "__name__", str(func)),
            "module": getattr(func, "__module__", None),
            "signature": str(signature),
            "parameters": list(signature.parameters.keys()),
            "doc": (func.__doc__ or "")[:200],
        }

    def get_frame_info(self, frame: Any) -> dict[str, Any]:
        """Return the frame info."""
        return {
            "filename": frame.f_code.co_filename,
            "lineno": frame.f_lineno,
            "function": frame.f_code.co_name,
            "locals": {k: repr(v)[:100] for k, v in frame.f_locals.items()},
        }

    def get_traceback_info(self) -> list[dict[str, Any]]:
        """Return the traceback info."""
        frames = []
        for frame_info in inspect.stack():
            frames.append({
                "filename": frame_info.filename,
                "lineno": frame_info.lineno,
                "function": frame_info.function,
            })
        return frames

    def is_async_function(self, obj: Any) -> bool:
        """Return whether async function holds for the current value."""
        return inspect.iscoroutinefunction(obj)

    def is_async_generator(self, obj: Any) -> bool:
        """Return whether async generator holds for the current value."""
        return inspect.isasyncgenfunction(obj)

    def get_source(self, obj: Any) -> str | None:
        """Return the source."""
        try:
            return inspect.getsource(obj)
        except (OSError, TypeError, ValueError):
            return None
