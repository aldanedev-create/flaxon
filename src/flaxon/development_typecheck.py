"""Nonblocking, development-only Teloce type checks on startup and saved inputs."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute

logger = logging.getLogger(__name__)


class DevelopmentTypecheck:
    """Own one checker task for an application's development lifespan."""

    def __init__(self, integration: Any) -> None:
        self.integration = integration
        self.task: asyncio.Task[None] | None = None
        self.revision: str | None = None
        self.result: Any = None
        self.error: str | None = None

    def fingerprint(self) -> str:
        """Include UI inputs, real TypeScript, and project configuration changes."""
        ui = self.integration
        digest = hashlib.sha256(ui._source_revision().encode())
        for directory, dirs, files in os.walk(ui.project_root):
            dirs[:] = sorted(
                name
                for name in dirs
                if name
                not in {
                    "node_modules",
                    ".git",
                    ".venv",
                    "venv",
                    "__pycache__",
                    ".flaxon",
                    "dist",
                    "build",
                }
                and not (Path(directory) / name).resolve().is_relative_to(ui.build_dir)
            )
            for name in sorted(files):
                if not name.endswith((".ts", ".tsx", ".json")):
                    continue
                path = Path(directory) / name
                try:
                    stat = path.stat()
                except FileNotFoundError:
                    continue
                digest.update(f"{path}:{stat.st_mtime_ns}:{stat.st_size}".encode())
        return digest.hexdigest()

    def check(self) -> None:
        """Report findings without making type errors fatal to the server."""
        ui = self.integration
        roots = [source.directory for source in ui.sources if source.directory.is_dir()]
        self.result, self.error = None, None
        if not roots:
            return
        try:
            check_project = import_attribute("teloce.typecheck", "check_project")
            self.result = check_project(roots, project_root=ui.project_root)
            for finding in self.result.findings[:100]:
                logger.warning("%s", finding.format())
                ui.debugger.record({
                    "category": "typecheck",
                    "message": finding.format(),
                    "component": finding.file,
                    "line": finding.line,
                    "column": finding.column,
                })
            if self.result.ok:
                logger.info("Teloce typecheck: no type errors found.")
        except Exception as error:
            self.error = str(error)
            logger.warning("Teloce typecheck could not run: %s", error)
            ui.debugger.record({"category": "typecheck", "message": f"Type checking could not run: {error}"})

    async def poll(self) -> None:
        """Check once per changed revision, including previously failing inputs."""
        revision = await asyncio.to_thread(self.fingerprint)
        if revision != self.revision:
            self.revision = revision
            worker = asyncio.create_task(asyncio.to_thread(self.check))
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                await worker
                raise

    async def start(self) -> None:
        """Start a single watcher only for an enabled development integration."""
        if not self.integration.app.debug or not self.integration.typecheck or self.task is not None:
            return
        self.task = asyncio.create_task(self.watch(), name="flaxon-teloce-typecheck")

    async def watch(self) -> None:
        """Keep checking saved inputs even when no browser is connected."""
        while True:
            try:
                await self.poll()
            except (OSError, ValueError) as error:
                logger.warning("Teloce typecheck watcher could not read inputs: %s", error)
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop polling and finish an in-flight compiler call before shutdown."""
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            finally:
                self.task = None
