from __future__ import annotations

from typing import Any


class AdminConfig:
    def __init__(
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

    def to_dict(self) -> dict[str, Any]:
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
        }
