"""
API routes package.

This package contains the route handlers for all API endpoints:
- health: System health checks
- stats: Index statistics
- search: Document search
- ingest: File ingestion
"""

from src.api.routes.health import check_health
from src.api.routes.stats import get_index_stats
from src.api.routes.search import perform_search
from src.api.routes.ingest import queue_file, queue_batch

__all__ = [
    "check_health",
    "get_index_stats", 
    "perform_search",
    "queue_file",
    "queue_batch",
]
