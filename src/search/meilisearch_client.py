"""
Meilisearch client for full-text search.

This module provides a client for Meilisearch search engine:
- Full-text search with typo tolerance
- Filterable and sortable attributes
- Fast keyword search to complement semantic search
- Hybrid search support with LanceDB
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

try:
    from meilisearch import Client
    from meilisearch.errors import MeilisearchApiError, MeilisearchCommunicationError
    MEILISEARCH_AVAILABLE = True
except ImportError:
    MEILISEARCH_AVAILABLE = False
    Client = None

try:
    from src.core.logger import get_logger
    from src.core.config import ConfigManager
except ImportError:
    from core.logger import get_logger
    from core.config import ConfigManager


class MeilisearchError(Exception):
    """Base exception for Meilisearch operations."""
    pass


class MeilisearchConnectionError(MeilisearchError):
    """Raised when connection to Meilisearch fails."""
    pass


class MeilisearchClient:
    """
    Client for Meilisearch full-text search operations.
    
    Provides fast keyword search with typo tolerance and filters.
    Designed to work alongside LanceDBClient for hybrid search.
    
    Attributes:
        client: Meilisearch client connection
        index_name: Name of the documents index
        host: Meilisearch server URL
    
    Example:
        >>> client = MeilisearchClient()
        >>> client.add_document({
        ...     "path": "/docs/file.pdf",
        ...     "title": "Important Document",
        ...     "content": "This is the document content..."
        ... })
        >>> results = client.search("important document")
    """
    
    # Default index settings for aitao documents
    DEFAULT_SETTINGS = {
        "searchableAttributes": [
            "title",
            "content",
            "path",
        ],
        "filterableAttributes": [
            "category",
            "language", 
            "file_type",
            "created_at",
        ],
        "sortableAttributes": [
            "created_at",
            "file_size",
            "title",
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 4,
                "twoTypos": 8,
            },
        },
        "pagination": {
            "maxTotalHits": 5000,
        },
    }
    
    def __init__(
        self,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        config: Optional[ConfigManager] = None,
        timeout: int = 30,
    ):
        """
        Initialize Meilisearch client.
        
        Args:
            host: Meilisearch server URL. Default: http://localhost:7700
            api_key: API key for authentication. Default: None (dev mode)
            index_name: Name of documents index. Default: aitao_documents
            config: ConfigManager instance. If None, creates new one.
            timeout: Request timeout in seconds.
        
        Raises:
            MeilisearchError: If meilisearch-python not installed
            MeilisearchConnectionError: If connection fails
        """
        if not MEILISEARCH_AVAILABLE:
            raise MeilisearchError(
                "meilisearch-python package not installed. "
                "Run: pip install meilisearch"
            )
        
        self.logger = get_logger("meilisearch")
        
        # Load configuration
        try:
            if config:
                self._config = config
            else:
                self._config = ConfigManager("config/config.yaml")
        except Exception:
            self._config = None
        
        # Determine connection settings
        # Config uses 'url' key, accept both 'host' param and config 'url'
        self.host = host or (
            self._config.get("search.meilisearch.url", "http://localhost:7700")
            if self._config else "http://localhost:7700"
        )
        
        # Handle empty string api_key as None
        config_api_key = (
            self._config.get("search.meilisearch.api_key", None)
            if self._config else None
        )
        if config_api_key == "":
            config_api_key = None
        self.api_key = api_key or config_api_key
        
        self.index_name = index_name or (
            self._config.get("search.meilisearch.index_name", "aitao_documents")
            if self._config else "aitao_documents"
        )
        
        self.timeout = timeout
        
        # Connect to Meilisearch
        self.logger.info(
            "Connecting to Meilisearch",
            metadata={"host": self.host, "index": self.index_name}
        )
        
        try:
            self.client = Client(self.host, self.api_key, timeout=timeout)
            
            # Test connection
            health = self.client.health()
            if health.get("status") != "available":
                raise MeilisearchConnectionError(
                    f"Meilisearch not healthy: {health}"
                )
                
        except MeilisearchCommunicationError as e:
            raise MeilisearchConnectionError(
                f"Cannot connect to Meilisearch at {self.host}: {e}"
            )
        except Exception as e:
            raise MeilisearchConnectionError(f"Connection failed: {e}")
        
        # Ensure index exists with proper settings
        self._ensure_index()
        
        self.logger.info(
            "Meilisearch client initialized",
            metadata={
                "host": self.host,
                "index": self.index_name,
            }
        )
    
    def _ensure_index(self) -> None:
        """Create index if it doesn't exist and configure settings."""
        try:
            # Try to get existing index
            try:
                self.index = self.client.get_index(self.index_name)
                self.logger.debug(
                    "Using existing index",
                    metadata={"index": self.index_name}
                )
            except MeilisearchApiError as e:
                if "index_not_found" in str(e):
                    # Create new index
                    task = self.client.create_index(
                        self.index_name,
                        {"primaryKey": "id"}
                    )
                    self._wait_for_task(task.task_uid)
                    self.index = self.client.get_index(self.index_name)
                    
                    # Apply default settings
                    task = self.index.update_settings(self.DEFAULT_SETTINGS)
                    self._wait_for_task(task.task_uid)
                    
                    self.logger.info(
                        "Created new index with settings",
                        metadata={"index": self.index_name}
                    )
                else:
                    raise
                    
        except Exception as e:
            raise MeilisearchError(f"Failed to ensure index: {e}")
    
    def _wait_for_task(self, task_uid: int, timeout_ms: int = 30000) -> Dict:
        """Wait for an async task to complete and return status dict."""
        try:
            task = self.client.wait_for_task(task_uid, timeout_ms)
            # meilisearch-python 0.40+ returns a Task object (Pydantic model)
            # Convert to dict for consistent handling
            if hasattr(task, 'model_dump'):
                return task.model_dump()
            elif hasattr(task, 'dict'):
                return task.dict()
            elif isinstance(task, dict):
                return task
            else:
                # Fallback: extract status attribute
                return {"status": getattr(task, 'status', 'unknown')}
        except Exception as e:
            self.logger.warning(
                "Task wait timeout",
                metadata={"task_uid": task_uid, "error": str(e)}
            )
            return {"status": "timeout"}
    
    def _generate_id(self, path: str) -> str:
        """Generate unique ID from file path using SHA256."""
        return hashlib.sha256(path.encode()).hexdigest()
    
    def add_document(
        self,
        path: str,
        title: str,
        content: str,
        category: str = "autre",
        language: str = "unknown",
        file_type: Optional[str] = None,
        file_size: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a document to the search index.
        
        Args:
            path: Absolute file path (used to generate ID)
            title: Document title
            content: Full text content to index
            category: Document category
            language: Detected language code
            file_type: File extension (e.g., ".pdf")
            file_size: File size in bytes
            metadata: Additional metadata as dict
        
        Returns:
            Document ID (SHA256 of path)
        
        Raises:
            MeilisearchError: If add operation fails
        """
        doc_id = self._generate_id(path)
        now = datetime.now(timezone.utc).isoformat()
        
        # Prepare document
        document = {
            "id": doc_id,
            "path": path,
            "title": title,
            "content": content[:100000] if content else "",  # Limit content size
            "category": category,
            "language": language,
            "file_type": file_type or Path(path).suffix,
            "file_size": file_size,
            "created_at": now,
            "updated_at": now,
        }
        
        # Add extra metadata fields if provided
        if metadata:
            for key, value in metadata.items():
                if key not in document:
                    # Meilisearch requires JSON-serializable values
                    if isinstance(value, (str, int, float, bool, list)):
                        document[key] = value
                    else:
                        document[key] = str(value)
        
        try:
            # Add or update document
            task = self.index.add_documents([document])
            result = self._wait_for_task(task.task_uid)
            
            if result.get("status") == "failed":
                raise MeilisearchError(f"Add failed: {result.get('error')}")
            
            self.logger.info(
                "Document added to index",
                metadata={
                    "id": doc_id,
                    "path": path,
                    "title": title[:50],
                }
            )
            
            return doc_id
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Failed to add document: {e}")
    
    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Add multiple documents in a single batch.
        
        Args:
            documents: List of document dicts with path, title, content, etc.
        
        Returns:
            List of document IDs
        
        Raises:
            MeilisearchError: If batch add fails
        """
        prepared = []
        doc_ids = []
        now = datetime.now(timezone.utc).isoformat()
        
        for doc in documents:
            path = doc.get("path", "")
            doc_id = self._generate_id(path)
            doc_ids.append(doc_id)
            
            prepared.append({
                "id": doc_id,
                "path": path,
                "title": doc.get("title", ""),
                "content": (doc.get("content", "") or "")[:100000],
                "category": doc.get("category", "autre"),
                "language": doc.get("language", "unknown"),
                "file_type": doc.get("file_type") or Path(path).suffix,
                "file_size": doc.get("file_size", 0),
                "created_at": now,
                "updated_at": now,
            })
        
        try:
            task = self.index.add_documents(prepared)
            result = self._wait_for_task(task.task_uid, timeout_ms=120000)
            
            if result.get("status") == "failed":
                raise MeilisearchError(f"Batch add failed: {result.get('error')}")
            
            self.logger.info(
                "Batch documents added",
                metadata={"count": len(prepared)}
            )
            
            return doc_ids
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Failed to add documents batch: {e}")
    
    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filter_category: Optional[str] = None,
        filter_language: Optional[str] = None,
        filter_file_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """
        Search documents using full-text search.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            offset: Offset for pagination
            filter_category: Filter by category (optional)
            filter_language: Filter by language (optional)
            filter_file_type: Filter by file type (optional)
            sort_by: Sort field (created_at, file_size, title)
            sort_order: Sort order (asc or desc)
        
        Returns:
            List of matching documents with scores
        
        Example:
            >>> results = client.search("facture 2025", limit=5)
            >>> for doc in results:
            ...     print(f"{doc['title']}")
        """
        # Build filter string
        filters = []
        if filter_category:
            filters.append(f'category = "{filter_category}"')
        if filter_language:
            filters.append(f'language = "{filter_language}"')
        if filter_file_type:
            filters.append(f'file_type = "{filter_file_type}"')
        
        filter_str = " AND ".join(filters) if filters else None
        
        # Build sort
        sort = None
        if sort_by:
            sort = [f"{sort_by}:{sort_order}"]
        
        try:
            result = self.index.search(
                query,
                {
                    "limit": limit,
                    "offset": offset,
                    "filter": filter_str,
                    "sort": sort,
                    "attributesToRetrieve": [
                        "id", "path", "title", "content", "category",
                        "language", "file_type", "file_size", "created_at"
                    ],
                    "attributesToCrop": ["content"],
                    "cropLength": 200,
                    "attributesToHighlight": ["title", "content"],
                }
            )
            
            # Format results
            formatted = []
            for hit in result.get("hits", []):
                formatted.append({
                    "id": hit.get("id"),
                    "path": hit.get("path"),
                    "title": hit.get("title"),
                    "content": hit.get("_formatted", {}).get("content", hit.get("content", ""))[:500],
                    "category": hit.get("category"),
                    "language": hit.get("language"),
                    "file_type": hit.get("file_type"),
                    "file_size": hit.get("file_size"),
                    "created_at": hit.get("created_at"),
                    "_highlights": hit.get("_formatted", {}),
                })
            
            self.logger.info(
                "Search completed",
                metadata={
                    "query": query[:50],
                    "results_count": len(formatted),
                    "total_hits": result.get("estimatedTotalHits", 0),
                    "processing_time_ms": result.get("processingTimeMs", 0),
                }
            )
            
            return formatted
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Search failed: {e}")
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete a document from the index.
        
        Args:
            doc_id: Document ID (SHA256 hash)
        
        Returns:
            True if deleted successfully
        """
        try:
            task = self.index.delete_document(doc_id)
            result = self._wait_for_task(task.task_uid)
            
            self.logger.info(
                "Document deleted",
                metadata={"id": doc_id}
            )
            
            return result.get("status") == "succeeded"
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Delete failed: {e}")
    
    def delete_by_path(self, path: str) -> bool:
        """
        Delete a document by its file path.
        
        Args:
            path: Absolute file path
        
        Returns:
            True if deleted successfully
        """
        doc_id = self._generate_id(path)
        return self.delete(doc_id)
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID (SHA256 hash)
        
        Returns:
            Document dict or None if not found
        """
        try:
            doc = self.index.get_document(doc_id)
            return dict(doc)
        except MeilisearchApiError as e:
            if "document_not_found" in str(e):
                return None
            raise MeilisearchError(f"Get document failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Dict with document count, field distribution, etc.
        """
        try:
            stats = self.index.get_stats()
            
            # meilisearch-python 0.40+ returns IndexStats Pydantic model
            # Convert to dict or access attributes directly
            if hasattr(stats, 'model_dump'):
                stats_dict = stats.model_dump()
            elif hasattr(stats, 'dict'):
                stats_dict = stats.dict()
            elif isinstance(stats, dict):
                stats_dict = stats
            else:
                # Access attributes directly
                stats_dict = {
                    "numberOfDocuments": getattr(stats, 'number_of_documents', 0),
                    "isIndexing": getattr(stats, 'is_indexing', False),
                    "fieldDistribution": getattr(stats, 'field_distribution', {}),
                }
            
            return {
                "total_documents": stats_dict.get("number_of_documents", 
                                   stats_dict.get("numberOfDocuments", 0)),
                "is_indexing": stats_dict.get("is_indexing",
                               stats_dict.get("isIndexing", False)),
                "field_distribution": stats_dict.get("field_distribution",
                                      stats_dict.get("fieldDistribution", {})),
                "index_name": self.index_name,
                "host": self.host,
            }
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Get stats failed: {e}")
    
    def clear(self) -> int:
        """
        Delete all documents from the index.
        
        Returns:
            Number of documents deleted
        """
        try:
            # Get count before clearing
            stats = self.get_stats()
            count = stats.get("total_documents", 0)
            
            task = self.index.delete_all_documents()
            self._wait_for_task(task.task_uid, timeout_ms=60000)
            
            self.logger.warning(
                "Index cleared",
                metadata={"deleted_count": count}
            )
            
            return count
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Clear failed: {e}")
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update index settings.
        
        Args:
            settings: Dict of settings to update
        
        Returns:
            True if updated successfully
        """
        try:
            task = self.index.update_settings(settings)
            result = self._wait_for_task(task.task_uid)
            
            self.logger.info(
                "Settings updated",
                metadata={"settings": list(settings.keys())}
            )
            
            return result.get("status") == "succeeded"
            
        except MeilisearchApiError as e:
            raise MeilisearchError(f"Update settings failed: {e}")
    
    def is_healthy(self) -> bool:
        """Check if Meilisearch server is healthy."""
        try:
            health = self.client.health()
            return health.get("status") == "available"
        except Exception:
            return False
    
    def get_version(self) -> str:
        """Get Meilisearch server version."""
        try:
            version = self.client.get_version()
            return version.get("pkgVersion", "unknown")
        except Exception:
            return "unknown"
