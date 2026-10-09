"""
Flaxon version information.

This module contains the version string and version info tuple for the framework.
"""

from __future__ import annotations

import re

__version__ = "0.2.7"
_version_match = re.match(r"^(\d+)\.(\d+)\.(\d+)", __version__)
if _version_match is None:
    raise ValueError("Flaxon version must start with major.minor.patch")
__version_info__ = tuple(int(x) for x in _version_match.groups())

# Alias for convenience
version_info = __version_info__


def get_version() -> str:
    """Return the current version string."""
    return __version__


def is_release() -> bool:
    """Return True if this is a release version (not alpha/beta/rc)."""
    return not (is_alpha() or is_beta() or is_rc() or is_dev())


def is_alpha() -> bool:
    """Return True if this is an alpha version."""
    return bool(re.search(r"(?:alpha|a)\d", __version__))


def is_beta() -> bool:
    """Return True if this is a beta version."""
    return bool(re.search(r"(?:beta|b)\d", __version__))


def is_rc() -> bool:
    """Return True if this is a release candidate."""
    return "rc" in __version__


def is_dev() -> bool:
    """Return True if this is a development version."""
    return "dev" in __version__ or "post" in __version__
