from __future__ import annotations

from .build import BuildCommand
from .docs import DocsCommand
from .doctor import DoctorCommand
from .generate import GenerateCommand
from .inspect import InspectCommand
from .migrate import MigrateCommand
from .new import NewCommand
from .routes import RoutesCommand
from .run import RunCommand
from .schedule import ScheduleCommand
from .shell import ShellCommand
from .test import TestCommand
from .version import VersionCommand
from .worker import WorkerCommand

__all__ = [
    "BuildCommand",
    "DocsCommand",
    "DoctorCommand",
    "GenerateCommand",
    "InspectCommand",
    "MigrateCommand",
    "NewCommand",
    "RoutesCommand",
    "RunCommand",
    "ScheduleCommand",
    "ShellCommand",
    "TestCommand",
    "VersionCommand",
    "WorkerCommand",
]
