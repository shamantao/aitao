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

from importlib.metadata import version as metadata_version, PackageNotFoundError
from pathlib import Path


def _read_version_from_pyproject() -> str:
    """Read version directly from pyproject.toml (single source of truth)."""
    # Try to find pyproject.toml relative to this file
    # version.py is in src/core/, pyproject.toml is at project root
    version_file = Path(__file__)
    project_root = version_file.parent.parent.parent  # src/core -> src -> project_root
    pyproject_path = project_root / "pyproject.toml"
    
    if pyproject_path.exists():
        try:
            import tomllib
        except ImportError:
            # Python < 3.11 fallback
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                return "0.0.0"
        
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "0.0.0")
    
    return "0.0.0"


def _get_version() -> str:
    """Get version from metadata or pyproject.toml."""
    try:
        return metadata_version("aitao")
    except PackageNotFoundError:
        # Fallback: read directly from pyproject.toml
        return _read_version_from_pyproject()


__version__ = _get_version()

# Semantic parts
VERSION_PARTS = __version__.split('.')
MAJOR = int(VERSION_PARTS[0]) if len(VERSION_PARTS) > 0 else 2
MINOR = int(VERSION_PARTS[1]) if len(VERSION_PARTS) > 1 else 0
PATCH = int(VERSION_PARTS[2]) if len(VERSION_PARTS) > 2 else 0


def get_version() -> str:
    """Return the current version string."""
    return __version__


def get_version_info() -> dict:
    """Return detailed version information."""
    import sys
    return {
        "version": __version__,
        "major": MAJOR,
        "sprint": MINOR,
        "user_story": PATCH,
        "codename": "Foundation" if MINOR == 0 else f"Sprint {MINOR}",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
