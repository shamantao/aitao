"""
AItao version information.

This module provides version information for the AItao package.
The single source of truth is pyproject.toml - this file reads from there.

Version format: MAJOR.MINOR.PATCH
  - MAJOR: Version (1=V1 legacy, 2=V2 modular)
  - MINOR: Sprint number (0=Foundation, 1=Indexation, etc.)
  - PATCH: User Story number within sprint

Example: 2.0.5 = V2, Sprint 0, US-005 completed
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("aitao")
except PackageNotFoundError:
    # Package not installed, fallback to hardcoded version
    __version__ = "2.0.5"

# Semantic parts
VERSION_PARTS = __version__.split('.')
MAJOR = int(VERSION_PARTS[0]) if len(VERSION_PARTS) > 0 else 2
MINOR = int(VERSION_PARTS[1]) if len(VERSION_PARTS) > 1 else 0
PATCH = int(VERSION_PARTS[2]) if len(VERSION_PARTS) > 2 else 0

# Human-readable version info
VERSION_INFO = {
    "version": __version__,
    "major": MAJOR,
    "sprint": MINOR,
    "user_story": PATCH,
    "codename": "Foundation" if MINOR == 0 else f"Sprint {MINOR}",
}


def get_version() -> str:
    """Return the current version string."""
    return __version__


def get_version_info() -> dict:
    """Return detailed version information."""
    return VERSION_INFO.copy()
