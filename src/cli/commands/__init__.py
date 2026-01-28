"""
CLI Commands module.

Each command is a separate module for maintainability and testability.
"""

from cli.commands import status
from cli.commands import meilisearch
from cli.commands import database
from cli.commands import config

__all__ = ["status", "meilisearch", "database", "config"]
