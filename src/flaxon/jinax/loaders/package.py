from __future__ import annotations

import importlib.resources
import os
from collections.abc import Callable
from typing import Any


class PackageLoader:
    def __init__(self, package_name: str, package_path: str = "templates", encoding: str = "utf-8") -> None:
        self.package_name = package_name
        self.package_path = package_path
        self.encoding = encoding
        self._cache: dict[str, tuple[str, float]] = {}

    def get_source(
        self, environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        try:
            full_path = f"{self.package_path}/{template}"
            resource = importlib.resources.files(self.package_name).joinpath(full_path)

            if not resource.exists():
                raise FileNotFoundError(f"Template '{template}' not found in package {self.package_name}")

            with importlib.resources.as_file(resource) as path:
                with open(path, encoding=self.encoding) as f:
                    source = f.read()

            mtime = os.path.getmtime(path)

            def uptodate() -> bool:
                try:
                    return os.path.getmtime(path) == mtime
                except OSError:
                    return False

            return source, str(path), uptodate

        except (FileNotFoundError, TypeError) as exc:
            raise FileNotFoundError(
                f"Template '{template}' not found in package {self.package_name}"
            ) from exc

    def list_templates(self) -> list[str]:
        try:
            resources = importlib.resources.files(self.package_name).joinpath(self.package_path)
            if not resources.exists():
                return []

            templates = []
            for item in resources.iterdir():
                if item.is_file():
                    templates.append(item.name)
            return templates

        except (FileNotFoundError, TypeError):
            return []

    def exists(self, template: str) -> bool:
        try:
            resource = importlib.resources.files(self.package_name).joinpath(
                f"{self.package_path}/{template}"
            )
            return resource.exists()
        except (FileNotFoundError, TypeError):
            return False
