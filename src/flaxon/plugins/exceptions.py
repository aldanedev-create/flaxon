from __future__ import annotations

from flaxon.exceptions import FlaxonError


class PluginError(FlaxonError):
    """Report a plugin failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class PluginNotFoundError(PluginError):
    """Report a plugin not found failure."""

    def __init__(self, message: str = "Plugin not found") -> None:
        """Perform the   init   operation for plugin not found error."""
        super().__init__(message)


class PluginLoadError(PluginError):
    """Report a plugin load failure."""

    def __init__(self, message: str = "Failed to load plugin") -> None:
        super().__init__(message)


class PluginRegistrationError(PluginError):
    """Report a plugin registration failure."""

    def __init__(self, message: str = "Failed to register plugin") -> None:
        super().__init__(message)


class PluginDiscoveryError(PluginError):
    """Report a plugin discovery failure."""

    def __init__(self, message: str = "Failed to discover plugin") -> None:
        super().__init__(message)
