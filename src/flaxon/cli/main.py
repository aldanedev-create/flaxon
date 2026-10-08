from __future__ import annotations

import argparse
import sys

from flaxon import __version__

from .console import Console
from .discovery import CommandDiscovery


def create_parser(*, include_project: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flaxon",
        description="Flaxon framework command line tools",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"Flaxon {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discovery = CommandDiscovery()
    commands = discovery.discover(include_project=include_project)

    for cmd in commands:
        cmd.add_parser(subparsers)

    parser.set_defaults(_commands={cmd.name: cmd for cmd in commands})
    return parser


def main() -> int:
    # Creating a project or printing a version must not import an existing app.
    first = sys.argv[1] if len(sys.argv) > 1 else ""
    parser = create_parser(include_project=first not in {"new", "version", "-v", "--version"})
    args = parser.parse_args()

    console = Console()

    commands = args._commands

    if args.command in commands:
        try:
            return commands[args.command].run(args, console)
        except Exception as exc:
            console.error(f"Error: {exc}")
            return 1

    console.error(f"Unknown command: {args.command}")
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
