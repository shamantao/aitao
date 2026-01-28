"""
Search engine for AItao V2.

Modules:
- lancedb_client: LanceDB wrapper (semantic search)
- meilisearch_client: Meilisearch wrapper (full-text search)
- hybrid_search: Hybrid search combining both engines
"""

from search.lancedb_client import LanceDBClient, LanceDBError
from search.meilisearch_client import (
    MeilisearchClient,
    MeilisearchError,
    MeilisearchConnectionError,
)

__all__ = [
    "LanceDBClient",
    "LanceDBError",
    "MeilisearchClient",
    "MeilisearchError",
    "MeilisearchConnectionError",
]
