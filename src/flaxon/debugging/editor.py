"""Editor links for development diagnostics.

`app.use_teloce(editor=...)` turns a mapped source location into a link that opens
the file in the developer's editor. It is a development convenience only: the link
is built from a validated template, only for files inside a registered Teloce
source directory, and only ever sent in debug responses.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

#: Built-in templates. `{path}` is the absolute file path and `{relpath}` the project-relative one.
EDITOR_PRESETS: dict[str, str] = {
    "vscode": "vscode://file/{path}:{line}:{column}",
    "vscode-insiders": "vscode-insiders://file/{path}:{line}:{column}",
    "vscode-remote": "vscode://vscode-remote/{remote}{path}:{line}:{column}",
}

#: Schemes that must never reach a browser, whatever a template or a mapped path says.
FORBIDDEN_SCHEMES = frozenset({"javascript", "data", "vbscript", "file"})

#: Placeholders a template may use. Anything else is a typo and is rejected.
PLACEHOLDERS = frozenset({"path", "relpath", "line", "column", "remote"})

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def in_codespaces(env: Mapping[str, str] | None = None) -> bool:
    """Report whether this process runs inside a GitHub Codespace.

    A `vscode://file/...` link points at a path inside the container, which the
    browser on the developer's machine cannot open, so the default preset stays
    off there unless the project configured an editor itself.
    """
    values: Mapping[str, str] = os.environ if env is None else env
    return bool(values.get("CODESPACES") or values.get("CODESPACE_NAME"))


def _validate_template(template: str, remote: str) -> None:
    """Reject a template that cannot produce a usable, safe editor URL."""
    if "{path}" not in template:
        raise ValueError("editor must be a preset name or a URL template containing {path}")
    unknown = sorted(set(_PLACEHOLDER.findall(template)) - PLACEHOLDERS)
    if unknown:
        raise ValueError(f"editor template uses unknown placeholders: {', '.join(unknown)}")
    scheme = urlsplit(template).scheme.lower()
    if scheme in FORBIDDEN_SCHEMES:
        raise ValueError(f"editor template must not use a {scheme}: URL")
    if "{remote}" in template and not remote:
        raise ValueError("editor_remote is required for an editor template using {remote}")


@dataclass(frozen=True, slots=True)
class EditorLink:
    """One validated editor configuration: a URL template, a remote prefix and a path map."""

    template: str | None = None
    remote: str = ""
    path_map: dict[str, str] = field(default_factory=dict)

    def url_for(self, path: str | Path, *, relpath: str, line: int, column: int) -> str | None:
        """Build an editor URL for a source file, or None when it cannot be built safely."""
        if not self.template:
            return None
        url = self.template.format(
            path=self._mapped(str(path)),
            relpath=relpath,
            line=max(1, int(line)),
            column=max(1, int(column)),
            remote=self.remote,
        )
        return url if urlsplit(url).scheme.lower() not in FORBIDDEN_SCHEMES else None

    def _mapped(self, absolute: str) -> str:
        """Rewrite a path prefix so a container path can become a host path."""
        for source in sorted(self.path_map, key=len, reverse=True):
            if absolute.startswith(source):
                return self.path_map[source] + absolute[len(source) :]
        return absolute


def resolve_editor(
    editor: str | None = "vscode",
    *,
    editor_remote: str | None = None,
    editor_path_map: dict[str, Any] | None = None,
    configured: bool = False,
) -> EditorLink:
    """Validate the `editor` option and return the resulting `EditorLink`.

    `editor` is a preset name (`vscode`, `vscode-insiders`, `vscode-remote`), a URL
    template containing `{path}`, or None to switch editor links off. In a Codespace
    the default preset produces a link that cannot open, so it stays off there
    unless the project passed `editor` or `editor_remote` itself.
    """
    remote = str(editor_remote or "").strip()
    path_map = {str(key): str(value) for key, value in (editor_path_map or {}).items()}
    if editor is None:
        return EditorLink(path_map=path_map)
    if in_codespaces() and not configured and not remote:
        return EditorLink(path_map=path_map)
    template = EDITOR_PRESETS.get(str(editor).strip().lower(), str(editor))
    _validate_template(template, remote)
    return EditorLink(template=template, remote=remote, path_map=path_map)
