from __future__ import annotations


class JinaxError(Exception):
    """Report a jinax failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class TemplateNotFoundError(JinaxError):
    """Report a template not found failure."""

    def __init__(self, template: str) -> None:
        super().__init__(f"Template '{template}' not found")
        self.template = template


# Preserve the established public exception import.
TemplateNotFound = TemplateNotFoundError


class TemplateSyntaxError(JinaxError):
    """Report a template syntax failure."""

    def __init__(self, message: str, line: int | None = None, column: int | None = None) -> None:
        location = f" at line {line}, column {column}" if line and column else ""
        super().__init__(f"{message}{location}")
        self.line = line
        self.column = column


class TemplateRenderError(JinaxError):
    """Report a template render failure."""

    def __init__(self, message: str, template: str | None = None) -> None:
        context = f" in template '{template}'" if template else ""
        super().__init__(f"{message}{context}")
        self.template = template


class TemplateLoaderError(JinaxError):
    """Report a template loader failure."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Template loader error: {message}")


class TemplateCacheError(JinaxError):
    """Report a template cache failure."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Template cache error: {message}")


class SandboxError(JinaxError):
    """Report a sandbox failure."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Sandbox error: {message}")


class MacroError(JinaxError):
    """Report a macro failure."""

    def __init__(self, message: str, macro: str | None = None) -> None:
        context = f" in macro '{macro}'" if macro else ""
        super().__init__(f"{message}{context}")
        self.macro = macro


class FilterError(JinaxError):
    """Report a filter failure."""

    def __init__(self, message: str, filter_name: str | None = None) -> None:
        context = f" in filter '{filter_name}'" if filter_name else ""
        super().__init__(f"{message}{context}")
        self.filter_name = filter_name


class InheritanceError(JinaxError):
    """Report a inheritance failure."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Inheritance error: {message}")


class EscapingError(JinaxError):
    """Report a escaping failure."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Escaping error: {message}")
