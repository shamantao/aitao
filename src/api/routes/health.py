"""
Health check endpoint handler.

This module provides system health monitoring:
- API status
- LanceDB connectivity
- Meilisearch connectivity
- Worker status
"""

import time
from datetime import datetime, timezone
from typing import Optional

from src.api.schemas import HealthResponse, ServiceStatus
from src.core.logger import get_logger

logger = get_logger("api.health")


async def check_service_lancedb() -> ServiceStatus:
    """Check LanceDB connectivity."""
    start = time.time()
    try:
        from src.search.lancedb_client import LanceDBClient
        client = LanceDBClient()
        stats = client.get_stats()
        latency = (time.time() - start) * 1000
        
        return ServiceStatus(
            name="lancedb",
            status="healthy",
            message=f"{stats.get('total_documents', 0)} documents indexed",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"LanceDB health check failed: {e}")
        return ServiceStatus(
            name="lancedb",
            status="down",
            message=str(e),
            latency_ms=round(latency, 2),
        )


async def check_service_meilisearch() -> ServiceStatus:
    """Check Meilisearch connectivity."""
    start = time.time()
    try:
        from src.search.meilisearch_client import MeilisearchClient
        client = MeilisearchClient()
        
        # Check if connected
        if not client.is_connected():
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                name="meilisearch",
                status="down",
                message="Not connected to Meilisearch server",
                latency_ms=round(latency, 2),
            )
        
        stats = client.get_stats()
        latency = (time.time() - start) * 1000
        
        return ServiceStatus(
            name="meilisearch",
            status="healthy",
            message=f"{stats.get('numberOfDocuments', 0)} documents indexed",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"Meilisearch health check failed: {e}")
        return ServiceStatus(
            name="meilisearch",
            status="down",
            message=str(e),
            latency_ms=round(latency, 2),
        )


async def check_service_worker() -> ServiceStatus:
    """Check background worker status."""
    try:
        from src.indexation.worker import BackgroundWorker
        worker = BackgroundWorker()
        
        if worker.is_running():
            return ServiceStatus(
                name="worker",
                status="healthy",
                message="Worker is running",
            )
        else:
            return ServiceStatus(
                name="worker",
                status="degraded",
                message="Worker is not running",
            )
    except Exception as e:
        logger.warning(f"Worker health check failed: {e}")
        return ServiceStatus(
            name="worker",
            status="degraded",
            message=str(e),
        )


async def check_health(start_time: Optional[float], version: str) -> HealthResponse:
    """
    Perform full health check on all services.
    
    Args:
        start_time: API start timestamp for uptime calculation
        version: API version string
    
    Returns:
        HealthResponse with status of all services
    """
    # Check all services
    lancedb_status = await check_service_lancedb()
    meilisearch_status = await check_service_meilisearch()
    worker_status = await check_service_worker()
    
    # API is always healthy if we reach this point
    api_status = ServiceStatus(
        name="api",
        status="healthy",
        message=f"Version {version}",
    )
    
    # Build services dict
    services = {
        "api": api_status,
        "lancedb": lancedb_status,
        "meilisearch": meilisearch_status,
        "worker": worker_status,
    }
    
    # Determine overall status
    # Critical services: lancedb and meilisearch (search capability)
    critical_services = [lancedb_status, meilisearch_status]
    all_critical_down = all(s.status == "down" for s in critical_services)
    
    statuses = [s.status for s in services.values()]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif all_critical_down:
        # System is down if both search backends are unavailable
        overall_status = "down"
    elif any(s == "down" for s in statuses):
        overall_status = "degraded"
    else:
        overall_status = "degraded"
    
    # Calculate uptime
    uptime = None
    if start_time:
        uptime = time.time() - start_time
    
    return HealthResponse(
        status=overall_status,
        version=version,
        timestamp=datetime.now(timezone.utc),
        services=services,
        uptime_seconds=round(uptime, 2) if uptime else None,
    )
