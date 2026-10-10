from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .templates import TemplateEngine


class Generator:
    """Generator implementation for the cli subsystem."""

    def __init__(self) -> None:
        self.templates = TemplateEngine()

    def generate(self, directory: Path, template: str = "fullstack") -> None:
        """Perform the generate operation for generator."""
        if template not in {"fullstack", "basic"}:
            raise ValueError(f"Unknown project template: {template}")
        if directory.exists():
            raise FileExistsError(f"Directory '{directory}' already exists")
        package_name = re.sub(r"[^a-z0-9]+", "-", directory.name.lower()).strip("-")
        if not package_name:
            raise ValueError("Project name must contain a letter or number")
        directory.mkdir(parents=True, exist_ok=False)
        if template == "fullstack":
            self._generate_fullstack(directory, package_name)
            return

        app_py = self.templates.render("app.py", {"name": directory.name})
        (directory / "app.py").write_text(app_py, encoding="utf-8")

        pyproject = self.templates.render("pyproject.toml", {"package_name": package_name})
        (directory / "pyproject.toml").write_text(pyproject, encoding="utf-8")

        gitignore = self.templates.render("gitignore")
        (directory / ".gitignore").write_text(gitignore, encoding="utf-8")

        readme = self.templates.render("README.md", {"name": directory.name})
        (directory / "README.md").write_text(readme, encoding="utf-8")

    def _generate_fullstack(self, directory: Path, package_name: str) -> None:
        starter = Path(__file__).with_name("starter")
        for source in sorted(starter.rglob("*.tmpl")):
            relative = source.relative_to(starter).with_suffix("")
            if relative.name == "env.example":
                relative = relative.with_name(".env.example")
            if relative.name == "gitignore":
                relative = relative.with_name(".gitignore")
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            content = source.read_text(encoding="utf-8")
            content = content.replace("__PROJECT_NAME_LITERAL__", repr(directory.name))
            content = content.replace("__PROJECT_NAME__", directory.name)
            content = content.replace("__PACKAGE_NAME__", package_name)
            target.write_text(content, encoding="utf-8")

    def generate_component(self, type: str, name: str, path: str | Path = ".") -> None:
        """Generate the component."""
        filename_map = {
            "controller": f"{name}_controller.py",
            "schema": f"{name}_schema.py",
            "service": f"{name}_service.py",
            "middleware": f"{name}_middleware.py",
        }

        filename = filename_map.get(type, f"{name}.py")

        template_content = self.templates.render(
            f"{type}.py", {"name": name, "name_capitalize": name.capitalize()}
        )
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        full_path = directory / filename

        if full_path.exists():
            raise FileExistsError(f"File '{full_path}' already exists")

        full_path.write_text(template_content, encoding="utf-8")

    def generate_from_string(self, template: str, context: dict[str, Any]) -> str:
        """Generate the from string."""
        return self.templates.render_string(template, context)
