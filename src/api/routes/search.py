"""
Search endpoint handler.

This module provides hybrid search functionality:
- Semantic search via LanceDB
- Full-text search via Meilisearch
- Parallel execution for performance
- Weighted result merging (60% semantic, 40% fulltext)
- Comprehensive filter support

Uses HybridSearchEngine for optimized parallel search.
"""

from typing import Optional

from fastapi import HTTPException

from src.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from src.core.logger import get_logger
from src.search.hybrid_engine import HybridSearchEngine, SearchFilter

logger = get_logger("api.search")

# Global engine instance (lazy-loaded)
_search_engine: Optional[HybridSearchEngine] = None


def get_search_engine() -> HybridSearchEngine:
    """Get or create the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = HybridSearchEngine()
    return _search_engine


async def perform_search(request: SearchRequest) -> SearchResponse:
    """
    Perform hybrid search across LanceDB and Meilisearch.
    
    Uses HybridSearchEngine for parallel execution and optimized merging.
    
    Args:
        request: Search request with query and filters
    
    Returns:
        SearchResponse with merged results
    """
    # Validate query
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    logger.info(f"Search request: '{query}'", metadata={
        "limit": request.limit,
        "mode": request.search_mode,
        "filters": {
            "path": request.path_contains,
            "category": request.category,
            "language": request.language,
        }
    })
    
    # Build search filters
    filters = SearchFilter(
        path_contains=request.path_contains,
        category=request.category,
        language=request.language,
        date_after=request.date_after,
        date_before=request.date_before,
    )
    
    # Execute hybrid search
    engine = get_search_engine()
    response = await engine.search(
        query=query,
        limit=request.limit,
        offset=request.offset,
        filters=filters,
        mode=request.search_mode,
    )
    
    # Convert to API response format
    results = [
        SearchResultItem(
            id=r.id,
            path=r.path,
            title=r.title,
            summary=r.content,
            score=r.score,
            category=r.category,
            language=r.language,
            file_size=r.file_size,
            modified_at=r.modified_at,
            word_count=r.metadata.get("word_count") if r.metadata else None,
        )
        for r in response.results
    ]
    
    logger.info(
        f"Search completed: {len(results)} results in {response.search_time_ms:.2f}ms",
        metadata={
            "lancedb_count": response.lancedb_count,
            "meilisearch_count": response.meilisearch_count,
            "lancedb_time_ms": response.lancedb_time_ms,
            "meilisearch_time_ms": response.meilisearch_time_ms,
        }
    )
    
    return SearchResponse(
        query=query,
        total=response.total,
        limit=request.limit,
        offset=request.offset,
        results=results,
        search_time_ms=response.search_time_ms,
    )

