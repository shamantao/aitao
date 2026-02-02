"""
Stats endpoint handler.

This module provides index statistics:
- LanceDB document count and size
- Meilisearch document count and size
- Queue statistics
- Storage usage
"""

from datetime import datetime, timezone
from typing import Optional

from src.api.schemas import StatsResponse, IndexStats
from src.core.logger import get_logger
from src.core.registry import StatsKeys

logger = get_logger("api.stats")


async def get_lancedb_stats() -> Optional[IndexStats]:
    """Get LanceDB index statistics."""
    try:
        from src.search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        stats = client.get_stats()
        
        return IndexStats(
            name="lancedb",
            document_count=stats.get(StatsKeys.TOTAL_DOCUMENTS, 0),
            size_bytes=stats.get("size_bytes"),
            last_updated=stats.get("last_updated"),
        )
    except Exception as e:
        logger.warning(f"Failed to get LanceDB stats: {e}")
        return None


async def get_meilisearch_stats() -> Optional[IndexStats]:
    """Get Meilisearch index statistics."""
    try:
        from src.search.meilisearch_client import MeilisearchClient
        client = MeilisearchClient()
        
        if not client.is_connected():
            return None
        
        stats = client.get_stats()
        
        return IndexStats(
            name="meilisearch",
            document_count=stats.get("numberOfDocuments", 0),
            size_bytes=stats.get("indexSize"),
            last_updated=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.warning(f"Failed to get Meilisearch stats: {e}")
        return None


async def get_queue_stats() -> Optional[dict]:
    """Get task queue statistics."""
    try:
        from src.indexation.queue import TaskQueue
        queue = TaskQueue()
        stats = queue.get_stats()
        
        return {
            "pending": stats.get("pending", 0),
            "processing": stats.get("processing", 0),
            "completed": stats.get("completed", 0),
            "failed": stats.get("failed", 0),
            "total": stats.get("total", 0),
        }
    except Exception as e:
        logger.warning(f"Failed to get queue stats: {e}")
        return None


async def get_storage_stats() -> Optional[dict]:
    """Get storage usage statistics."""
    try:
        from src.core.pathmanager import path_manager
        import shutil
        
        storage_root = path_manager.get_storage_root()
        
        # Get disk usage
        total, used, free = shutil.disk_usage(storage_root)
        
        return {
            "storage_root": str(storage_root),
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "used_percent": round((used / total) * 100, 2),
        }
    except Exception as e:
        logger.warning(f"Failed to get storage stats: {e}")
        return None


async def get_index_stats() -> StatsResponse:
    """
    Get comprehensive index statistics.
    
    Returns stats for LanceDB, Meilisearch, queue, and storage.
    """
    lancedb_stats = await get_lancedb_stats()
    meilisearch_stats = await get_meilisearch_stats()
    queue_stats = await get_queue_stats()
    storage_stats = await get_storage_stats()
    
    # Calculate total documents
    total = 0
    if lancedb_stats:
        total = max(total, lancedb_stats.document_count)
    if meilisearch_stats:
        total = max(total, meilisearch_stats.document_count)
    
    return StatsResponse(
        total_documents=total,
        lancedb=lancedb_stats,
        meilisearch=meilisearch_stats,
        queue=queue_stats,
        storage=storage_stats,
    )
