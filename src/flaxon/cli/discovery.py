from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from flaxon._imports import import_module

from .base import Command
from .commands import (
    BuildCommand,
    DocsCommand,
    DoctorCommand,
    GenerateCommand,
    InspectCommand,
    MigrateCommand,
    NewCommand,
    RoutesCommand,
    RunCommand,
    ScheduleCommand,
    ShellCommand,
    TestCommand,
    VersionCommand,
    WorkerCommand,
)


class CommandDiscovery:
    """Command discovery implementation for the cli subsystem."""

    def __init__(self) -> None:
        self._builtin_commands = [
            RunCommand(),
            RoutesCommand(),
            DoctorCommand(),
            NewCommand(),
            GenerateCommand(),
            DocsCommand(),
            BuildCommand(),
            InspectCommand(),
            MigrateCommand(),
            ScheduleCommand(),
            ShellCommand(),
            TestCommand(),
            VersionCommand(),
            WorkerCommand(),
        ]

    def discover(self, *, include_project: bool = True) -> list[Command]:
        """Perform the discover operation for command discovery."""
        commands = list(self._builtin_commands)

        if not include_project:
            return commands

        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        try:
            flaxon_cli = import_module("flaxon_cli")

            commands.extend(self._discover_from_module(flaxon_cli))
        except ImportError:
            pass

        if Path("cli").exists():
            commands.extend(self._discover_from_path("cli"))

        return commands

    def _discover_from_module(self, module: Any) -> list[Command]:
        commands = []

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, Command):
                commands.append(attr)

        return commands

    def _discover_from_path(self, path: str) -> list[Command]:
        commands = []
        path_obj = Path(path)

        if not path_obj.exists():
            return commands

        for file_path in path_obj.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                commands.extend(self._discover_from_module(module))

            except Exception:
                logging.getLogger(__name__).warning("Could not load custom command module %s", file_path)
                continue

        return commands
