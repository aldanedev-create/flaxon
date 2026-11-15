"""The project templates offered by ``flaxon new``.

Each template is a complete, tested starting point. Pick the smallest one that fits;
nothing stops you adding capabilities later.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_TEMPLATE = "fullstack"


@dataclass(frozen=True)
class ProjectTemplate:
    """One ``flaxon new --template`` choice."""

    name: str
    summary: str
    includes: str
    #: Directory under ``flaxon/cli`` holding ``*.tmpl`` files; ``None`` for the inline basic app.
    source: str | None
    #: Commands to print after generation, each following the project's Python executable.
    steps: tuple[str, ...]


TEMPLATES: dict[str, ProjectTemplate] = {
    template.name: template
    for template in (
        ProjectTemplate(
            name="basic",
            summary="A single-file app: the smallest possible start.",
            includes="routes, health endpoint",
            source=None,
            steps=("-m flaxon run app:app --reload",),
        ),
        ProjectTemplate(
            name="api",
            summary="A modular JSON API with OpenAPI docs and tests.",
            includes="modules, OpenAPI docs, trusted hosts, pytest",
            source="starters/api",
            steps=("-m flaxon run app:app --reload", "-m pytest"),
        ),
        ProjectTemplate(
            name="api-db",
            summary="A JSON API backed by a database, with migrations and tests.",
            includes="API + Tortoise ORM, migrations, management commands, pytest",
            source="starters/api-db",
            steps=(
                "management.py check",
                "management.py makemigrations",
                "management.py migrate",
                "management.py runserver",
                "-m pytest",
            ),
        ),
        ProjectTemplate(
            name="web",
            summary="A server-rendered website with Jinax templates (no JavaScript build).",
            includes="Jinax templates, static files, escaping, pytest",
            source="starters/web",
            steps=("-m flaxon run app:app --reload", "-m pytest"),
        ),
        ProjectTemplate(
            name="fullstack",
            summary="Modular app with Teloce UI, Jinax, ORM, migrations and Admin/CMS.",
            includes="everything above + Teloce SPA, Admin/CMS",
            source="starter",
            steps=(
                "management.py check",
                "-m flaxon welcome",
                "management.py makemigrations",
                "management.py migrate",
                "management.py setup-admin",
                "management.py runserver",
            ),
        ),
    )
}


def template_names() -> list[str]:
    """Names accepted by ``--template`` in presentation order."""
    return list(TEMPLATES)


def detect_template(directory: Path) -> str:
    """Best-effort template for an existing project (used when resuming setup).

    Based on files only, so projects edited by hand still resolve sensibly.
    """

    def has(name: str) -> bool:
        return (directory / name).exists()

    if has("admin.py") and has("management.py"):
        return "fullstack"
    if has("management.py"):
        return "api-db"
    if has("templates") and has("app.py"):
        return "web"
    if has("modules") and has("app.py"):
        return "api"
    return "basic"
