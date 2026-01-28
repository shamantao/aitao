"""
Search endpoint handler.

This module provides hybrid search functionality:
- Semantic search via LanceDB
- Full-text search via Meilisearch
- Result merging and ranking
- Filter support
"""

import time
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException

from src.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from src.core.logger import get_logger

logger = get_logger("api.search")


async def search_lancedb(
    query: str,
    limit: int,
    path_contains: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
) -> List[dict]:
    """
    Perform semantic search via LanceDB.
    
    Returns list of results with scores normalized to 0-1.
    """
    try:
        from src.search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        
        results = client.search(
            query=query,
            limit=limit * 2,  # Get more for merging
            path_filter=path_contains,
        )
        
        # Apply additional filters
        filtered = []
        for r in results:
            if category and r.get("category") != category:
                continue
            if language and r.get("language") != language:
                continue
            filtered.append(r)
        
        return filtered[:limit]
    except Exception as e:
        logger.warning(f"LanceDB search failed: {e}")
        return []


async def search_meilisearch(
    query: str,
    limit: int,
    path_contains: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    date_after: Optional[datetime] = None,
    date_before: Optional[datetime] = None,
) -> List[dict]:
    """
    Perform full-text search via Meilisearch.
    
    Returns list of results with scores normalized to 0-1.
    """
    try:
        from src.search.meilisearch_client import MeilisearchClient
        client = MeilisearchClient()
        
        if not client.is_connected():
            return []
        
        # Build filters
        filters = []
        if path_contains:
            filters.append(f"path CONTAINS '{path_contains}'")
        if category:
            filters.append(f"category = '{category}'")
        if language:
            filters.append(f"language = '{language}'")
        if date_after:
            filters.append(f"modified_at >= {int(date_after.timestamp())}")
        if date_before:
            filters.append(f"modified_at <= {int(date_before.timestamp())}")
        
        filter_str = " AND ".join(filters) if filters else None
        
        results = client.search(
            query=query,
            limit=limit * 2,
            filters=filter_str,
        )
        
        return results[:limit]
    except Exception as e:
        logger.warning(f"Meilisearch search failed: {e}")
        return []


def merge_results(
    lancedb_results: List[dict],
    meilisearch_results: List[dict],
    limit: int,
    semantic_weight: float = 0.6,
) -> List[SearchResultItem]:
    """
    Merge and rank results from both search engines.
    
    Uses weighted scoring: 60% semantic (LanceDB), 40% full-text (Meilisearch).
    """
    # Build score map by document ID
    scores = {}  # id -> {semantic_score, fulltext_score, doc}
    
    # Process LanceDB results (semantic)
    for i, result in enumerate(lancedb_results):
        doc_id = result.get("id", result.get("path", str(i)))
        # Normalize score: rank-based if no score provided
        score = result.get("score", 1.0 - (i / max(len(lancedb_results), 1)))
        
        if doc_id not in scores:
            scores[doc_id] = {"doc": result, "semantic": 0, "fulltext": 0}
        scores[doc_id]["semantic"] = score
        scores[doc_id]["doc"] = result
    
    # Process Meilisearch results (full-text)
    for i, result in enumerate(meilisearch_results):
        doc_id = result.get("id", result.get("path", str(i)))
        # Normalize score: rank-based
        score = 1.0 - (i / max(len(meilisearch_results), 1))
        
        if doc_id not in scores:
            scores[doc_id] = {"doc": result, "semantic": 0, "fulltext": 0}
        scores[doc_id]["fulltext"] = score
        # Prefer Meilisearch doc if available (has highlights)
        if result.get("title"):
            scores[doc_id]["doc"] = result
    
    # Calculate combined scores
    ranked = []
    for doc_id, data in scores.items():
        combined_score = (
            data["semantic"] * semantic_weight +
            data["fulltext"] * (1 - semantic_weight)
        )
        ranked.append((combined_score, data["doc"]))
    
    # Sort by combined score
    ranked.sort(key=lambda x: x[0], reverse=True)
    
    # Convert to SearchResultItem
    results = []
    for score, doc in ranked[:limit]:
        # Get summary (first 500 chars of content)
        content = doc.get("content", "")
        summary = content[:500] + "..." if len(content) > 500 else content
        
        results.append(SearchResultItem(
            id=doc.get("id", doc.get("path", "")),
            path=doc.get("path", ""),
            title=doc.get("title", doc.get("path", "").split("/")[-1]),
            summary=summary,
            score=round(min(1.0, max(0.0, score)), 4),
            category=doc.get("category"),
            language=doc.get("language"),
            file_size=doc.get("file_size") or doc.get("size"),
            modified_at=doc.get("modified_at"),
            word_count=doc.get("word_count"),
        ))
    
    return results


async def perform_search(request: SearchRequest) -> SearchResponse:
    """
    Perform hybrid search across LanceDB and Meilisearch.
    
    Args:
        request: Search request with query and filters
    
    Returns:
        SearchResponse with merged results
    """
    start_time = time.time()
    
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
    
    # Perform searches based on mode
    lancedb_results = []
    meilisearch_results = []
    
    if request.search_mode in ("hybrid", "semantic"):
        lancedb_results = await search_lancedb(
            query=query,
            limit=request.limit,
            path_contains=request.path_contains,
            category=request.category,
            language=request.language,
        )
    
    if request.search_mode in ("hybrid", "fulltext"):
        meilisearch_results = await search_meilisearch(
            query=query,
            limit=request.limit,
            path_contains=request.path_contains,
            category=request.category,
            language=request.language,
            date_after=request.date_after,
            date_before=request.date_before,
        )
    
    # Merge results
    if request.search_mode == "semantic":
        results = merge_results(lancedb_results, [], request.limit, semantic_weight=1.0)
    elif request.search_mode == "fulltext":
        results = merge_results([], meilisearch_results, request.limit, semantic_weight=0.0)
    else:
        results = merge_results(lancedb_results, meilisearch_results, request.limit)
    
    # Calculate search time
    search_time_ms = (time.time() - start_time) * 1000
    
    logger.info(f"Search completed: {len(results)} results in {search_time_ms:.2f}ms")
    
    return SearchResponse(
        query=query,
        total=len(results),
        limit=request.limit,
        offset=request.offset,
        results=results[request.offset:request.offset + request.limit],
        search_time_ms=round(search_time_ms, 2),
    )
