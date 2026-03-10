"""
Search engine for AItao V2.

Modules:
- lancedb_client: LanceDB wrapper (semantic search)
- meilisearch_client: Meilisearch wrapper (full-text search)
- hybrid_engine: Hybrid search combining both engines + chunk search for RAG
"""

from src.search.lancedb_client import LanceDBClient, LanceDBError
from src.search.meilisearch_client import (
    MeilisearchClient,
    MeilisearchError,
    MeilisearchConnectionError,
)
from src.search.hybrid_engine import (
    HybridSearchEngine,
    HybridSearchResponse,
    SearchResult,
    SearchFilter,
    ChunkSearchResult,
    ChunkSearchResponse,
)

__all__ = [
    # LanceDB
    "LanceDBClient",
    "LanceDBError",
    # Meilisearch
    "MeilisearchClient",
    "MeilisearchError",
    "MeilisearchConnectionError",
    # Hybrid Engine
    "HybridSearchEngine",
    "HybridSearchResponse",
    "SearchResult",
    "SearchFilter",
    # Chunk Search (RAG)
    "ChunkSearchResult",
    "ChunkSearchResponse",
]
