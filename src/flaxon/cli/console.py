from __future__ import annotations

import sys
from typing import Any


class Console:
    def __init__(self, color: bool = True) -> None:
        self.color = color
        self._colors = {
            "reset": "\033[0m",
            "bold": "\033[1m",
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
        }

    def _colorize(self, text: str, color: str) -> str:
        if not self.color:
            return text
        return f"{self._colors.get(color, '')}{text}{self._colors['reset']}"

    def info(self, message: str) -> None:
        print(self._colorize(message, "blue"), flush=True)

    def success(self, message: str) -> None:
        print(self._colorize(message, "green"), flush=True)

    def warning(self, message: str) -> None:
        print(self._colorize(message, "yellow"), flush=True)

    def error(self, message: str) -> None:
        print(self._colorize(message, "red"), file=sys.stderr, flush=True)

    def debug(self, message: str) -> None:
        print(self._colorize(message, "cyan"))

    def table(self, headers: list[str], rows: list[list[Any]]) -> None:
        if not rows:
            return

        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        header_line = "  ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
        print(self._colorize(header_line, "bold"))
        print("-" * len(header_line))

        for row in rows:
            line = "  ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
            print(line)

    def progress(self, current: int, total: int, prefix: str = "") -> None:
        percent = (current / total) * 100
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)

        message = f"{prefix} [{bar}] {percent:.1f}% ({current}/{total})"
        print(message, end="\r")

        if current == total:
            print()

    def confirm(self, message: str) -> bool:
        response = input(f"{message} (y/N): ").strip().lower()
        return response in {"y", "yes"}

    def input(self, prompt: str) -> str:
        return input(prompt).strip()

    def clear(self) -> None:
        print("\033[2J\033[H")
