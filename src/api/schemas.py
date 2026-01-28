"""
Pydantic schemas for AItao REST API.

This module defines request and response models for all API endpoints:
- Search: query, filters, results
- Ingest: file ingestion requests
- Health: system health status
- Stats: index statistics
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Search Schemas
# ============================================================================

class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    
    # Filters
    path_contains: Optional[str] = Field(None, description="Filter by path substring")
    category: Optional[str] = Field(None, description="Filter by document category")
    language: Optional[str] = Field(None, description="Filter by language (e.g., 'en', 'fr', 'zh')")
    date_after: Optional[datetime] = Field(None, description="Filter documents modified after this date")
    date_before: Optional[datetime] = Field(None, description="Filter documents modified before this date")
    
    # Search options
    search_mode: str = Field(default="hybrid", description="Search mode: 'hybrid', 'semantic', 'fulltext'")


class SearchResultItem(BaseModel):
    """Single search result item."""
    id: str = Field(..., description="Document ID (SHA256 hash)")
    path: str = Field(..., description="File path")
    title: str = Field(..., description="Document title or filename")
    summary: str = Field(..., description="Text excerpt/summary (first 500 chars)")
    score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    
    # Metadata
    category: Optional[str] = Field(None, description="Document category")
    language: Optional[str] = Field(None, description="Detected language")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    modified_at: Optional[datetime] = Field(None, description="Last modification date")
    word_count: Optional[int] = Field(None, description="Word count")


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str = Field(..., description="Original search query")
    total: int = Field(..., description="Total number of matching documents")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")
    results: List[SearchResultItem] = Field(default_factory=list, description="Search results")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")


# ============================================================================
# Ingest Schemas
# ============================================================================

class IngestRequest(BaseModel):
    """Request model for ingest endpoint."""
    file_path: str = Field(..., description="Absolute path to file to ingest")
    priority: str = Field(default="normal", description="Ingestion priority: 'high', 'normal', 'low'")
    force: bool = Field(default=False, description="Force re-indexing even if file already indexed")


class IngestBatchRequest(BaseModel):
    """Request model for batch ingest endpoint."""
    file_paths: List[str] = Field(..., min_length=1, max_length=1000, description="List of file paths")
    priority: str = Field(default="normal", description="Ingestion priority")


class IngestResponse(BaseModel):
    """Response model for ingest endpoint."""
    success: bool = Field(..., description="Whether ingestion was queued successfully")
    message: str = Field(..., description="Status message")
    task_id: Optional[str] = Field(None, description="Task ID for tracking")
    file_path: str = Field(..., description="File path that was queued")


class IngestBatchResponse(BaseModel):
    """Response model for batch ingest endpoint."""
    success: bool = Field(..., description="Whether all files were queued")
    queued: int = Field(..., description="Number of files queued")
    skipped: int = Field(..., description="Number of files skipped")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed files")


# ============================================================================
# Health Schemas
# ============================================================================

class ServiceStatus(BaseModel):
    """Status of a single service."""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Status: 'healthy', 'degraded', 'down'")
    message: Optional[str] = Field(None, description="Status message or error")
    latency_ms: Optional[float] = Field(None, description="Response time in ms")


class HealthResponse(BaseModel):
    """Response model for health endpoint."""
    status: str = Field(..., description="Overall status: 'healthy', 'degraded', 'down'")
    version: str = Field(..., description="AItao version")
    timestamp: datetime = Field(..., description="Check timestamp")
    services: Dict[str, ServiceStatus] = Field(..., description="Individual service statuses")
    uptime_seconds: Optional[float] = Field(None, description="API uptime in seconds")


# ============================================================================
# Stats Schemas
# ============================================================================

class IndexStats(BaseModel):
    """Statistics for a search index."""
    name: str = Field(..., description="Index name")
    document_count: int = Field(..., description="Number of indexed documents")
    size_bytes: Optional[int] = Field(None, description="Index size in bytes")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class StatsResponse(BaseModel):
    """Response model for stats endpoint."""
    total_documents: int = Field(..., description="Total indexed documents")
    lancedb: Optional[IndexStats] = Field(None, description="LanceDB statistics")
    meilisearch: Optional[IndexStats] = Field(None, description="Meilisearch statistics")
    queue: Optional[Dict[str, int]] = Field(None, description="Queue statistics")
    storage: Optional[Dict[str, Any]] = Field(None, description="Storage usage")


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
