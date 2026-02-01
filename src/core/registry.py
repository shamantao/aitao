"""
Central Interface Registry for AItao.

This module provides a single source of truth for all shared interfaces,
function signatures, and data structures. It prevents bugs caused by:
- Inconsistent attribute names (e.g., result.error vs result.error_message)
- Mismatched function parameters across modules
- Hardcoded values that should be centralized

Usage:
    from src.core.registry import (
        ConfigKeys, PathKeys, IndexResult, SearchResult
    )

Design Principle (AC-005):
    If a data structure or constant is used by more than one module,
    it MUST be defined here. Modules import from registry, never duplicate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# Configuration Keys (prevent typos in config access)
# ============================================================================

class ConfigKeys:
    """
    Centralized config.yaml key paths.
    
    Usage:
        config.get(ConfigKeys.STORAGE_ROOT)
        config.get(ConfigKeys.LANCEDB_PATH)
    """
    # Paths
    STORAGE_ROOT = "paths.storage_root"
    LANCEDB_PATH = "paths.lancedb_path"
    QUEUE_PATH = "paths.queue_path"
    LOGS_DIR = "paths.logs_dir"
    MODELS_DIR = "paths.models_dir"
    
    # Search - Meilisearch
    MEILISEARCH_HOST = "search.meilisearch.host"
    MEILISEARCH_API_KEY = "search.meilisearch.api_key"
    MEILISEARCH_INDEX = "search.meilisearch.index_name"
    
    # Search - LanceDB
    LANCEDB_TABLE = "search.lancedb.table_name"
    EMBEDDING_MODEL = "search.lancedb.embedding_model"
    OFFLINE_MODE = "search.lancedb.offline_mode"
    
    # Search - Hybrid weights
    MEILISEARCH_WEIGHT = "search.hybrid_search.meilisearch_weight"
    LANCEDB_WEIGHT = "search.hybrid_search.lancedb_weight"
    
    # Worker
    WORKER_POLL_INTERVAL = "indexing.worker.poll_interval"
    WORKER_CPU_THRESHOLD = "indexing.worker.cpu_threshold"
    WORKER_BATCH_SIZE = "indexing.worker.batch_size"
    
    # API
    API_HOST = "api.host"
    API_PORT = "api.port"
    API_CORS_ORIGINS = "api.cors_origins"
    
    # LLM
    OLLAMA_HOST = "llm.ollama.host"
    OLLAMA_DEFAULT_MODEL = "llm.ollama.default_model"
    RAG_ENABLED = "llm.rag.enabled"
    RAG_MAX_CONTEXT_DOCS = "llm.rag.max_context_docs"
    LLM_MODELS = "llm.models"
    LLM_STARTUP_CHECK_MODELS = "llm.startup.check_models"
    LLM_STARTUP_AUTO_PULL = "llm.startup.auto_pull"
    LLM_STARTUP_PULL_TIMEOUT = "llm.startup.pull_timeout_minutes"


# ============================================================================
# Task & Queue Structures
# ============================================================================

class TaskStatus(str, Enum):
    """Task status values (must match queue.py)."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority levels."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskType(str, Enum):
    """Types of indexing tasks."""
    INDEX = "index"
    REINDEX = "reindex"
    DELETE = "delete"
    OCR = "ocr"
    TRANSLATE = "translate"


@dataclass
class Task:
    """
    Task structure for the indexing queue.
    
    Canonical definition - all modules must use this structure.
    """
    id: str
    file_path: str
    task_type: TaskType = TaskType.INDEX
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    added_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None  # NOTE: 'error' not 'error_message'
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Indexing Results
# ============================================================================

@dataclass
class IndexResult:
    """
    Result of indexing a document.
    
    IMPORTANT: Use 'error' not 'error_message' for error details.
    This is the canonical structure - worker.py and indexer.py must use this.
    """
    success: bool
    doc_id: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None  # NOTE: 'error' not 'error_message'
    word_count: int = 0
    language: Optional[str] = None
    extraction_time_ms: float = 0.0
    indexing_time_ms: float = 0.0
    lancedb_success: bool = False
    meilisearch_success: bool = False


# ============================================================================
# Search Results
# ============================================================================

@dataclass
class SearchResult:
    """
    Single search result item.
    
    Canonical structure for hybrid search results.
    """
    id: str
    path: str
    title: str
    summary: str = ""
    score: float = 0.0
    source: str = "hybrid"  # "lancedb", "meilisearch", "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """
    Complete search response.
    """
    query: str
    results: List[SearchResult]
    total_count: int
    lancedb_count: int = 0
    meilisearch_count: int = 0
    query_time_ms: float = 0.0


# ============================================================================
# Health Check Structures
# ============================================================================

class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """
    Health status of a single service.
    """
    name: str
    status: ServiceStatus
    message: str = ""
    latency_ms: Optional[float] = None


@dataclass
class SystemHealth:
    """
    Overall system health.
    """
    status: ServiceStatus
    version: str
    services: Dict[str, ServiceHealth]
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# Document Structures
# ============================================================================

@dataclass
class Document:
    """
    Indexed document structure.
    
    Used by both LanceDB and Meilisearch indexing.
    """
    id: str  # SHA256 hash
    path: str
    title: str
    content: str
    language: str = "en"
    category: Optional[str] = None
    date_indexed: datetime = field(default_factory=datetime.now)
    date_modified: Optional[datetime] = None
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# API Endpoints Registry
# ============================================================================

class APIEndpoints:
    """
    Registry of API endpoints.
    
    Prevents hardcoding endpoint paths in multiple places.
    """
    # Core API
    HEALTH = "/api/health"              # Fast minimal check (API responding?)
    HEALTH_DEBUG = "/api/health/debug"  # Slow detailed diagnostics (all services)
    STATS = "/api/stats"
    SEARCH = "/api/search"
    INGEST = "/api/ingest"
    
    # Ollama-compatible
    CHAT = "/api/chat"
    GENERATE = "/api/generate"
    TAGS = "/api/tags"
    EMBEDDINGS = "/api/embeddings"
    
    # OpenAI-compatible
    V1_CHAT = "/v1/chat/completions"
    V1_MODELS = "/v1/models"
    V1_EMBEDDINGS = "/v1/embeddings"


# ============================================================================
# Default Values
# ============================================================================

class Defaults:
    """
    Default values that should be consistent across modules.
    """
    # Timeouts
    HTTP_TIMEOUT = 30  # seconds
    WORKER_POLL_INTERVAL = 30  # seconds
    API_SHUTDOWN_TIMEOUT = 10  # seconds
    
    # Limits
    MAX_SEARCH_RESULTS = 100
    MAX_BATCH_SIZE = 50
    MAX_RETRIES = 3
    
    # Ports
    API_PORT = 5000
    MEILISEARCH_PORT = 7700
    OLLAMA_PORT = 11434
    
    # Models
    EMBEDDING_MODEL = "BAAI/bge-m3"
    LLM_MODEL = "qwen2.5-coder:7b"
    
    # Search weights
    MEILISEARCH_WEIGHT = 0.4
    LANCEDB_WEIGHT = 0.6


# ============================================================================
# LLM Model Management Structures (AC-005)
# ============================================================================

class ModelRole(str, Enum):
    """Role/purpose of a model."""
    CHAT = "chat"
    CODE = "code"
    VISION = "vision"
    EMBEDDING = "embedding"
    RAG = "rag"
    OCR = "ocr"


@dataclass
class ModelInfo:
    """
    Configuration for a single LLM model.
    
    Canonical structure for model configuration and verification.
    """
    name: str                           # Model name in Ollama (e.g., "llama3.1:8b")
    required: bool = False              # Blocks startup if missing
    size_gb: Optional[float] = None     # Size info for user (e.g., 4.7)
    roles: List[ModelRole] = field(default_factory=list)  # Usage: chat, code, vision, etc.
    description: str = ""               # User-friendly description


@dataclass
class ModelStatus:
    """
    Status of models (present/missing/extra).
    
    Result of ModelManager.check_models().
    """
    present: List[str]                  # Models configured AND installed
    missing: List[str]                  # Models configured BUT not installed
    extra: List[str]                    # Models installed BUT not configured
    required_missing: List[str]         # Critical: required models that are missing


# ============================================================================
# Singleton Access Functions
# ============================================================================

def get_config():
    """
    Get the global ConfigManager instance.
    
    This is the ONLY way to access config. Never instantiate ConfigManager directly.
    See AC-001 in PRD.
    """
    from src.core.config import get_config as _get_config
    return _get_config()


def get_logger(name: str):
    """
    Get a structured logger instance.
    
    All modules should use this, never use print() in production.
    See AC-003 in PRD.
    """
    from src.core.logger import get_logger as _get_logger
    return _get_logger(name)
