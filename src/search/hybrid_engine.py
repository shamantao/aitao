"""
Hybrid Search Engine for AItao.

This module provides the HybridSearchEngine class that combines:
- Semantic search via LanceDB (embeddings-based similarity)
- Full-text search via Meilisearch (keyword matching with typo tolerance)
- Parallel execution for performance
- Weighted result merging (configurable 60/40 default)
- Comprehensive filtering support

The hybrid approach ensures both conceptual matches (semantic) and 
exact keyword matches (fulltext) are found.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.logger import get_logger

logger = get_logger("search.hybrid")


@dataclass
class SearchFilter:
    """
    Filtering options for hybrid search.
    
    Attributes:
        path_contains: Substring that must appear in document path
        category: Exact category match
        language: Language code (e.g., 'en', 'fr', 'zh')
        date_after: Documents modified after this date
        date_before: Documents modified before this date
        file_types: List of allowed file extensions (e.g., ['.pdf', '.docx'])
    """
    path_contains: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    date_after: Optional[datetime] = None
    date_before: Optional[datetime] = None
    file_types: Optional[List[str]] = None


@dataclass
class SearchResult:
    """
    Single search result with combined scoring.
    
    Attributes:
        id: Document ID (SHA256 hash)
        path: Absolute file path
        title: Document title or filename
        content: Text excerpt (first 500 chars)
        score: Combined relevance score (0-1)
        semantic_score: Score from LanceDB search (0-1)
        fulltext_score: Score from Meilisearch search (0-1)
        category: Document category
        language: Detected language
        file_size: Size in bytes
        modified_at: Last modification datetime
        metadata: Additional document metadata
    """
    id: str
    path: str
    title: str
    content: str
    score: float
    semantic_score: float = 0.0
    fulltext_score: float = 0.0
    category: Optional[str] = None
    language: Optional[str] = None
    file_size: Optional[int] = None
    modified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridSearchResponse:
    """
    Complete response from hybrid search.
    
    Attributes:
        query: Original search query
        results: List of SearchResult objects
        total: Total number of results found
        lancedb_count: Number of results from LanceDB
        meilisearch_count: Number of results from Meilisearch
        search_time_ms: Total search time in milliseconds
        lancedb_time_ms: LanceDB search time
        meilisearch_time_ms: Meilisearch search time
        mode: Search mode used (hybrid, semantic, fulltext)
    """
    query: str
    results: List[SearchResult]
    total: int
    lancedb_count: int = 0
    meilisearch_count: int = 0
    search_time_ms: float = 0.0
    lancedb_time_ms: float = 0.0
    meilisearch_time_ms: float = 0.0
    mode: str = "hybrid"


class HybridSearchEngine:
    """
    Hybrid search engine combining semantic and full-text search.
    
    Uses LanceDB for semantic vector similarity search and Meilisearch
    for fast full-text search with typo tolerance. Results are merged
    using configurable weighting (default: 60% semantic, 40% fulltext).
    
    Searches are executed in parallel for optimal performance, targeting
    <3 second latency for 500K documents.
    
    Example:
        >>> engine = HybridSearchEngine()
        >>> response = await engine.search("facture voyage Allemagne")
        >>> for result in response.results:
        ...     print(f"{result.title}: {result.score:.2f}")
    """
    
    # Default weights for result merging
    DEFAULT_SEMANTIC_WEIGHT = 0.6
    DEFAULT_FULLTEXT_WEIGHT = 0.4
    
    def __init__(
        self,
        semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
        max_workers: int = 2,
    ):
        """
        Initialize hybrid search engine.
        
        Args:
            semantic_weight: Weight for semantic (LanceDB) results (0-1).
                           Fulltext weight = 1 - semantic_weight.
            max_workers: Max threads for parallel search execution.
        """
        self.semantic_weight = semantic_weight
        self.fulltext_weight = 1 - semantic_weight
        self.max_workers = max_workers
        
        # Lazy-loaded clients
        self._lancedb_client = None
        self._meilisearch_client = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(
            "HybridSearchEngine initialized",
            metadata={
                "semantic_weight": self.semantic_weight,
                "fulltext_weight": self.fulltext_weight,
                "max_workers": max_workers,
            }
        )
    
    @property
    def lancedb_client(self):
        """Lazy-load LanceDB client."""
        if self._lancedb_client is None:
            try:
                from src.search.lancedb_client import LanceDBClient
                self._lancedb_client = LanceDBClient()
            except Exception as e:
                logger.warning(f"Failed to initialize LanceDB: {e}")
                self._lancedb_client = None
        return self._lancedb_client
    
    @property
    def meilisearch_client(self):
        """Lazy-load Meilisearch client."""
        if self._meilisearch_client is None:
            try:
                from src.search.meilisearch_client import MeilisearchClient
                self._meilisearch_client = MeilisearchClient()
            except Exception as e:
                logger.warning(f"Failed to initialize Meilisearch: {e}")
                self._meilisearch_client = None
        return self._meilisearch_client
    
    def _search_lancedb_sync(
        self,
        query: str,
        limit: int,
        filters: SearchFilter,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute LanceDB search synchronously (for thread pool).
        
        Returns:
            Tuple of (results list, execution time in ms)
        """
        start = time.time()
        results = []
        
        if self.lancedb_client is None:
            return results, 0.0
        
        try:
            raw_results = self.lancedb_client.search(
                query=query,
                limit=limit * 2,  # Get more for filtering
                filter_category=filters.category,
                filter_language=filters.language,
            )
            
            # Apply additional filters
            for r in raw_results:
                # Path filter
                if filters.path_contains:
                    if filters.path_contains.lower() not in r.get("path", "").lower():
                        continue
                
                # File type filter
                if filters.file_types:
                    file_type = r.get("file_type", "")
                    if file_type not in filters.file_types:
                        continue
                
                results.append(r)
                if len(results) >= limit:
                    break
            
        except Exception as e:
            logger.warning(f"LanceDB search error: {e}")
        
        elapsed_ms = (time.time() - start) * 1000
        return results, elapsed_ms
    
    def _search_meilisearch_sync(
        self,
        query: str,
        limit: int,
        filters: SearchFilter,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute Meilisearch search synchronously (for thread pool).
        
        Returns:
            Tuple of (results list, execution time in ms)
        """
        start = time.time()
        results = []
        
        if self.meilisearch_client is None:
            return results, 0.0
        
        try:
            # Meilisearch has its own filter syntax
            raw_results = self.meilisearch_client.search(
                query=query,
                limit=limit * 2,
                filter_category=filters.category,
                filter_language=filters.language,
            )
            
            # Apply additional filters not supported by Meilisearch directly
            for r in raw_results:
                # Path filter
                if filters.path_contains:
                    if filters.path_contains.lower() not in r.get("path", "").lower():
                        continue
                
                # Date filters
                if filters.date_after or filters.date_before:
                    created_at = r.get("created_at")
                    if created_at:
                        try:
                            doc_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            if filters.date_after and doc_date < filters.date_after:
                                continue
                            if filters.date_before and doc_date > filters.date_before:
                                continue
                        except ValueError:
                            pass
                
                # File type filter
                if filters.file_types:
                    file_type = r.get("file_type", "")
                    if file_type not in filters.file_types:
                        continue
                
                results.append(r)
                if len(results) >= limit:
                    break
            
        except Exception as e:
            logger.warning(f"Meilisearch search error: {e}")
        
        elapsed_ms = (time.time() - start) * 1000
        return results, elapsed_ms
    
    async def _search_parallel(
        self,
        query: str,
        limit: int,
        filters: SearchFilter,
        mode: str,
    ) -> Tuple[List[Dict], List[Dict], float, float]:
        """
        Execute searches in parallel using thread pool.
        
        Returns:
            Tuple of (lancedb_results, meilisearch_results, lance_time, meili_time)
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        
        lancedb_results = []
        meilisearch_results = []
        lancedb_time = 0.0
        meilisearch_time = 0.0
        
        # Determine which searches to run
        run_lancedb = mode in ("hybrid", "semantic")
        run_meilisearch = mode in ("hybrid", "fulltext")
        
        # Execute in parallel - only create tasks for engines we need
        tasks = []
        task_types = []  # Track which task is which
        
        if run_lancedb:
            tasks.append(
                loop.run_in_executor(
                    self._executor,
                    self._search_lancedb_sync,
                    query,
                    limit,
                    filters,
                )
            )
            task_types.append("lancedb")
        
        if run_meilisearch:
            tasks.append(
                loop.run_in_executor(
                    self._executor,
                    self._search_meilisearch_sync,
                    query,
                    limit,
                    filters,
                )
            )
            task_types.append("meilisearch")
        
        if not tasks:
            return lancedb_results, meilisearch_results, lancedb_time, meilisearch_time
        
        # Wait for all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Parse results based on task types
        for i, task_type in enumerate(task_types):
            if i < len(results) and not isinstance(results[i], Exception):
                if task_type == "lancedb":
                    lancedb_results, lancedb_time = results[i]
                elif task_type == "meilisearch":
                    meilisearch_results, meilisearch_time = results[i]
            elif isinstance(results[i], Exception):
                logger.warning(f"{task_type} parallel search error: {results[i]}")
        
        return lancedb_results, meilisearch_results, lancedb_time, meilisearch_time
    
    def _normalize_score(
        self,
        score: Optional[float],
        rank: int,
        total: int,
    ) -> float:
        """
        Normalize score to 0-1 range.
        
        Uses the provided score if valid, otherwise falls back to rank-based scoring.
        
        Args:
            score: Original score (may be distance for LanceDB)
            rank: Result rank (0-indexed)
            total: Total number of results
        
        Returns:
            Normalized score between 0 and 1
        """
        if score is not None and isinstance(score, (int, float)):
            # LanceDB returns _score already normalized
            if 0 <= score <= 1:
                return float(score)
            # May be a distance - convert
            return 1.0 / (1.0 + abs(score))
        
        # Fallback: rank-based scoring (higher rank = higher score)
        if total <= 1:
            return 1.0
        return 1.0 - (rank / total)
    
    def _merge_results(
        self,
        lancedb_results: List[Dict[str, Any]],
        meilisearch_results: List[Dict[str, Any]],
        limit: int,
    ) -> List[SearchResult]:
        """
        Merge and rank results from both search engines.
        
        Uses weighted scoring based on semantic_weight and fulltext_weight.
        Documents appearing in both result sets get boosted.
        
        Args:
            lancedb_results: Results from semantic search
            meilisearch_results: Results from full-text search
            limit: Maximum results to return
        
        Returns:
            Sorted list of SearchResult objects
        """
        # Score accumulator: doc_id -> {semantic, fulltext, doc}
        scores: Dict[str, Dict[str, Any]] = {}
        
        # Process LanceDB results
        lance_total = len(lancedb_results) or 1
        for rank, result in enumerate(lancedb_results):
            doc_id = result.get("id", result.get("path", str(rank)))
            
            raw_score = result.get("_score", result.get("score"))
            normalized = self._normalize_score(raw_score, rank, lance_total)
            
            if doc_id not in scores:
                scores[doc_id] = {
                    "semantic": 0.0,
                    "fulltext": 0.0,
                    "doc": result,
                }
            scores[doc_id]["semantic"] = normalized
            scores[doc_id]["doc"] = result
        
        # Process Meilisearch results
        meili_total = len(meilisearch_results) or 1
        for rank, result in enumerate(meilisearch_results):
            doc_id = result.get("id", result.get("path", str(rank)))
            
            # Meilisearch doesn't return numeric scores, use rank-based
            normalized = self._normalize_score(None, rank, meili_total)
            
            if doc_id not in scores:
                scores[doc_id] = {
                    "semantic": 0.0,
                    "fulltext": 0.0,
                    "doc": result,
                }
            scores[doc_id]["fulltext"] = normalized
            
            # Prefer Meilisearch doc if it has highlights
            if result.get("_highlights"):
                scores[doc_id]["doc"] = result
        
        # Calculate combined scores and sort
        ranked: List[Tuple[float, float, float, Dict]] = []
        for doc_id, data in scores.items():
            semantic_score = data["semantic"]
            fulltext_score = data["fulltext"]
            
            # Weighted combination
            combined = (
                semantic_score * self.semantic_weight +
                fulltext_score * self.fulltext_weight
            )
            
            # Bonus for appearing in both (overlap boost: +10%)
            if semantic_score > 0 and fulltext_score > 0:
                combined = min(1.0, combined * 1.1)
            
            ranked.append((combined, semantic_score, fulltext_score, data["doc"]))
        
        # Sort by combined score descending
        ranked.sort(key=lambda x: x[0], reverse=True)
        
        # Convert to SearchResult objects
        results: List[SearchResult] = []
        for combined, semantic, fulltext, doc in ranked[:limit]:
            # Extract content preview
            content = doc.get("content", "")
            summary = content[:500] + "..." if len(content) > 500 else content
            
            # Parse modified_at if string
            modified_at = doc.get("modified_at") or doc.get("created_at")
            if isinstance(modified_at, str):
                try:
                    modified_at = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
                except ValueError:
                    modified_at = None
            
            results.append(SearchResult(
                id=doc.get("id", doc.get("path", "")),
                path=doc.get("path", ""),
                title=doc.get("title") or doc.get("path", "").split("/")[-1],
                content=summary,
                score=round(combined, 4),
                semantic_score=round(semantic, 4),
                fulltext_score=round(fulltext, 4),
                category=doc.get("category"),
                language=doc.get("language"),
                file_size=doc.get("file_size"),
                modified_at=modified_at,
                metadata=doc.get("metadata", {}),
            ))
        
        return results
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[SearchFilter] = None,
        mode: str = "hybrid",
    ) -> HybridSearchResponse:
        """
        Execute hybrid search.
        
        Runs semantic and full-text searches in parallel, then merges
        results using weighted scoring.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Offset for pagination
            filters: Optional SearchFilter for filtering results
            mode: Search mode - 'hybrid', 'semantic', or 'fulltext'
        
        Returns:
            HybridSearchResponse with merged results
        
        Example:
            >>> engine = HybridSearchEngine()
            >>> filters = SearchFilter(category="factures", language="fr")
            >>> response = await engine.search("voyage", filters=filters)
        """
        start_time = time.time()
        
        # Validate query
        query = query.strip()
        if not query:
            return HybridSearchResponse(
                query=query,
                results=[],
                total=0,
                mode=mode,
            )
        
        # Default filters
        if filters is None:
            filters = SearchFilter()
        
        # Adjust limit for offset handling (get more, then slice)
        fetch_limit = limit + offset
        
        logger.info(
            f"Hybrid search: '{query}'",
            metadata={
                "limit": limit,
                "offset": offset,
                "mode": mode,
                "filters": {
                    "path": filters.path_contains,
                    "category": filters.category,
                    "language": filters.language,
                },
            }
        )
        
        # Execute parallel search
        lancedb_results, meilisearch_results, lance_time, meili_time = await self._search_parallel(
            query=query,
            limit=fetch_limit,
            filters=filters,
            mode=mode,
        )
        
        # Adjust weights based on mode
        original_semantic = self.semantic_weight
        original_fulltext = self.fulltext_weight
        
        if mode == "semantic":
            self.semantic_weight = 1.0
            self.fulltext_weight = 0.0
        elif mode == "fulltext":
            self.semantic_weight = 0.0
            self.fulltext_weight = 1.0
        
        # Merge results
        all_results = self._merge_results(
            lancedb_results,
            meilisearch_results,
            fetch_limit,
        )
        
        # Restore weights
        self.semantic_weight = original_semantic
        self.fulltext_weight = original_fulltext
        
        # Apply offset
        paginated = all_results[offset:offset + limit]
        
        # Calculate total time
        total_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Search completed: {len(paginated)} results",
            metadata={
                "total_results": len(all_results),
                "lancedb_count": len(lancedb_results),
                "meilisearch_count": len(meilisearch_results),
                "total_time_ms": round(total_time_ms, 2),
                "lancedb_time_ms": round(lance_time, 2),
                "meilisearch_time_ms": round(meili_time, 2),
            }
        )
        
        return HybridSearchResponse(
            query=query,
            results=paginated,
            total=len(all_results),
            lancedb_count=len(lancedb_results),
            meilisearch_count=len(meilisearch_results),
            search_time_ms=round(total_time_ms, 2),
            lancedb_time_ms=round(lance_time, 2),
            meilisearch_time_ms=round(meili_time, 2),
            mode=mode,
        )
    
    def search_sync(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[SearchFilter] = None,
        mode: str = "hybrid",
    ) -> HybridSearchResponse:
        """
        Synchronous version of search for non-async contexts.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Offset for pagination
            filters: Optional SearchFilter
            mode: Search mode
        
        Returns:
            HybridSearchResponse
        """
        # Try to get running loop, if any
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context, create new loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self.search(query, limit, offset, filters, mode)
                )
                return future.result()
        except RuntimeError:
            # No running loop, we can safely use asyncio.run
            return asyncio.run(self.search(query, limit, offset, filters, mode))
    
    def close(self):
        """Clean up resources."""
        self._executor.shutdown(wait=False)
