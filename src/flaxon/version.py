"""
Flaxon version information.

This module contains the version string and version info tuple for the framework.
"""

from __future__ import annotations

__version__ = "0.2.5"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# Alias for convenience
version_info = __version_info__


def get_version() -> str:
    """Return the current version string."""
    return __version__


def is_release() -> bool:
    """Return True if this is a release version (not alpha/beta/rc)."""
    return not any(part in __version__ for part in ("alpha", "beta", "rc", "dev"))


def is_alpha() -> bool:
    """Return True if this is an alpha version."""
    return "alpha" in __version__


def is_beta() -> bool:
    """Return True if this is a beta version."""
    return "beta" in __version__


def is_rc() -> bool:
    """Return True if this is a release candidate."""
    return "rc" in __version__


def is_dev() -> bool:
    """Return True if this is a development version."""
    return "dev" in __version__ or "post" in __version__
