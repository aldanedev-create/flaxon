from __future__ import annotations

from typing import Any


class AdminConfig:
    """Admin config implementation for the admin subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        site_title: str = "Flaxon Admin",
        site_header: str = "Flaxon Administration",
        index_title: str = "Welcome to Flaxon Admin",
        enable_dark_mode: bool = True,
        enable_search: bool = True,
        enable_actions: bool = True,
        enable_filters: bool = True,
        enable_pagination: bool = True,
        logo_url: str | None = None,
        custom_styles: str | None = None,
        custom_scripts: str | None = None,
        timezone: str = "UTC",
        settings: dict[str, Any] | None = None,
        action_bulk_limit: int = 1000,
        allow_impersonation: bool = False,
        import_max_rows: int = 5000,
        import_max_bytes: int = 5 * 1024 * 1024,
        enable_extensions: bool = True,
        disabled_extensions: tuple[str, ...] = (),
        extensions: list[Any] | None = None,
    ) -> None:
        self.site_title = site_title
        self.site_header = site_header
        self.index_title = index_title
        self.enable_dark_mode = enable_dark_mode
        self.enable_search = enable_search
        self.enable_actions = enable_actions
        self.enable_filters = enable_filters
        self.enable_pagination = enable_pagination
        self.logo_url = logo_url
        self.custom_styles = custom_styles
        self.custom_scripts = custom_scripts
        self.timezone = timezone
        self.settings = dict(settings or {})
        self.action_bulk_limit = action_bulk_limit
        # Impersonation is opt-in: enabling it must be a deliberate decision.
        self.allow_impersonation = allow_impersonation
        self.import_max_rows = import_max_rows
        self.import_max_bytes = import_max_bytes
        # Extensions are installed packages; discovery can be turned off or
        # narrowed, and explicit instances are always allowed.
        self.enable_extensions = enable_extensions
        self.disabled_extensions = tuple(disabled_extensions)
        self.extensions = list(extensions or [])

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "site_title": self.site_title,
            "site_header": self.site_header,
            "index_title": self.index_title,
            "enable_dark_mode": self.enable_dark_mode,
            "enable_search": self.enable_search,
            "enable_actions": self.enable_actions,
            "enable_filters": self.enable_filters,
            "enable_pagination": self.enable_pagination,
            "logo_url": self.logo_url,
            "custom_styles": self.custom_styles,
            "custom_scripts": self.custom_scripts,
            "timezone": self.timezone,
            "settings": self.settings,
            "action_bulk_limit": self.action_bulk_limit,
            "allow_impersonation": self.allow_impersonation,
            "import_max_rows": self.import_max_rows,
            "import_max_bytes": self.import_max_bytes,
            "enable_extensions": self.enable_extensions,
            "disabled_extensions": list(self.disabled_extensions),
            "extensions": [type(item).__name__ for item in self.extensions],
        }
