"""
LanceDB client for semantic vector search.

This module provides a client for LanceDB vector database:
- Local vector storage for semantic search
- Sentence-transformers embeddings
- CRUD operations on documents
- Hybrid search support
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

try:
    from src.core.logger import get_logger
    from src.core.config import ConfigManager, get_config
    from src.core.registry import StatsKeys
    from src.core.pathmanager import path_manager
except ImportError:
    from core.logger import get_logger
    from core.config import ConfigManager, get_config
    from core.registry import StatsKeys
    from core.pathmanager import path_manager


class LanceDBError(Exception):
    """Base exception for LanceDB operations."""
    pass


class LanceDBClient:
    """
    Client for LanceDB vector database operations.
    
    Provides semantic search capabilities using sentence-transformers
    embeddings stored in a local LanceDB instance.
    
    Attributes:
        db: LanceDB database connection
        table_name: Name of the documents table
        embedding_model: SentenceTransformer model for embeddings
        dimension: Embedding vector dimension
    
    Example:
        >>> client = LanceDBClient()
        >>> client.add_document({
        ...     "path": "/docs/file.pdf",
        ...     "title": "Important Document",
        ...     "content": "This is the document content..."
        ... })
        >>> results = client.search("important information")
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        table_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        config: Optional[ConfigManager] = None,
        load_model: bool = True,
        ensure_table: bool = True,
    ):
        """
        Initialize LanceDB client.
        
        Args:
            db_path: Path to LanceDB directory. If None, uses config.
            table_name: Name of documents table. Default: "aitao_embeddings"
            embedding_model: Sentence-transformers model name. 
                           Default: "BAAI/bge-m3" or from config
            config: ConfigManager instance. If None, uses global singleton.
        
        Raises:
            LanceDBError: If initialization fails
        """
        self.logger = get_logger("lancedb")
        
        # Load configuration (use global singleton for consistent paths)
        try:
            if config:
                self._config = config
            else:
                self._config = get_config()
        except Exception:
            # Fallback if config not available
            self._config = None
        
        # Determine paths and settings
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use PathManager for vector DB path resolution
            self.db_path = path_manager.get_vector_db_path()
        
        self.table_name = table_name or (
            self._config.get("search.lancedb.table_name", "aitao_embeddings")
            if self._config else "aitao_embeddings"
        )
        
        model_name = embedding_model or (
            self._config.get("search.lancedb.embedding_model", "BAAI/bge-m3")
            if self._config else "sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Check if offline mode is enabled (avoid HuggingFace API calls)
        offline_mode = (
            self._config.get("search.lancedb.offline_mode", False)
            if self._config else False
        )
        
        # Initialize embedding model (optional for lightweight operations)
        self._embedding_model = None
        self.dimension = None
        if load_model:
            self.logger.info(
                "Loading embedding model",
                metadata={"model": model_name, "offline": offline_mode}
            )
            try:
                # Set environment variable for HuggingFace offline mode
                if offline_mode:
                    import os
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
                
                self._embedding_model = SentenceTransformer(
                    model_name,
                    local_files_only=offline_mode
                )
                self.dimension = self._embedding_model.get_sentence_embedding_dimension()
            except Exception as e:
                raise LanceDBError(f"Failed to load embedding model: {e}")
        
        # Connect to database
        self.logger.info(
            "Connecting to LanceDB",
            metadata={"path": str(self.db_path)}
        )
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
            self.db = lancedb.connect(str(self.db_path))
        except Exception as e:
            raise LanceDBError(f"Failed to connect to LanceDB: {e}")
        
        # Ensure table exists
        if ensure_table:
            self._ensure_table()
        
        self.logger.info(
            "LanceDB client initialized",
            metadata={
                "db_path": str(self.db_path),
                "table": self.table_name,
                "embedding_dim": self.dimension,
            }
        )

    def _resolve_dimension_from_table(self) -> Optional[int]:
        """Resolve embedding dimension from existing table schema."""
        try:
            table = self.db.open_table(self.table_name)
            schema = table.schema
            vector_field = schema.field("vector")
            vector_type = vector_field.type
            list_size = getattr(vector_type, "list_size", None)
            return list_size if isinstance(list_size, int) else None
        except Exception:
            return None
    
    def _get_schema(self) -> pa.Schema:
        """Generate schema with correct vector dimension."""
        return pa.schema([
            pa.field("id", pa.string()),           # SHA256 hash of path
            pa.field("path", pa.string()),          # Absolute file path
            pa.field("title", pa.string()),         # Document title
            pa.field("content", pa.string()),       # Full text content
            pa.field("category", pa.string()),      # Document category
            pa.field("language", pa.string()),      # Detected language
            pa.field("file_type", pa.string()),     # File extension
            pa.field("file_size", pa.int64()),      # Size in bytes
            pa.field("created_at", pa.string()),    # ISO timestamp
            pa.field("updated_at", pa.string()),    # ISO timestamp
            pa.field("metadata", pa.string()),      # JSON string for extra data
            # Use FixedSizeList for vector column - required by LanceDB
            pa.field("vector", pa.list_(pa.float32(), self.dimension)),
        ])
    
    def _ensure_table(self) -> None:
        """Create table if it doesn't exist."""
        try:
            # list_tables() returns ListTablesResponse, extract table names
            tables_response = self.db.list_tables()
            table_names = (
                tables_response.tables 
                if hasattr(tables_response, 'tables') 
                else list(tables_response)
            )
            
            if self.table_name not in table_names:
                # Create empty table with dynamic schema
                self.db.create_table(
                    self.table_name,
                    schema=self._get_schema(),
                    mode="create"
                )
                self.logger.info(
                    "Created new table",
                    metadata={"table": self.table_name}
                )
        except Exception as e:
            raise LanceDBError(f"Failed to ensure table: {e}")
    
    def _generate_id(self, path: str) -> str:
        """Generate unique ID from file path using SHA256."""
        return hashlib.sha256(path.encode()).hexdigest()
    
    def _embed_text(self, text: str, allow_empty: bool = False) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            allow_empty: If True, return zero vector for empty text.
                         If False (default), raise ValueError.
        
        Returns:
            List of floats representing the embedding vector.
        
        Raises:
            ValueError: If text is empty and allow_empty is False.
        """
        if not text or not text.strip():
            if allow_empty:
                # Return zero vector for empty text (query case)
                return [0.0] * self.dimension
            else:
                raise ValueError("Cannot embed empty text - document has no content")
        
        if not self._embedding_model:
            raise LanceDBError("Embedding model not loaded")
        embedding = self._embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
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
        Add a document to the vector index.
        
        Args:
            path: Absolute file path (used to generate ID)
            title: Document title
            content: Full text content to embed
            category: Document category
            language: Detected language code
            file_type: File extension (e.g., ".pdf")
            file_size: File size in bytes
            metadata: Additional metadata as dict
        
        Returns:
            Document ID (SHA256 of path)
        
        Raises:
            ValueError: If content is empty or whitespace only
            LanceDBError: If add operation fails
        """
        # Validate content - reject empty documents
        if not content or not content.strip():
            self.logger.warning(
                "Skipping empty document",
                metadata={"path": path, "title": title}
            )
            raise ValueError(
                f"Cannot index document with empty content: {title}"
            )
        
        doc_id = self._generate_id(path)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Generate embedding (will also validate content)
        embedding = self._embed_text(content)
        
        # Prepare document record
        record = {
            "id": doc_id,
            "path": path,
            "title": title,
            "content": content[:10000] if content else "",  # Limit content size
            "category": category,
            "language": language,
            "file_type": file_type or Path(path).suffix,
            "file_size": file_size,
            "created_at": now,
            "updated_at": now,
            "metadata": json.dumps(metadata or {}),
            "vector": embedding,
        }
        
        try:
            table = self.db.open_table(self.table_name)
            
            # Check if document already exists (update if so)
            # Use lance scanner with filter instead of vector search
            df = table.to_pandas()
            existing = df[df["id"] == doc_id].to_dict(orient="records")
            
            if existing:
                # Delete existing and add updated
                table.delete(f"id = '{doc_id}'")
                self.logger.debug(
                    "Updating existing document",
                    metadata={"id": doc_id, "path": path}
                )
            
            # Add document
            table.add([record])
            
            self.logger.info(
                "Document added to index",
                metadata={
                    "id": doc_id,
                    "path": path,
                    "title": title,
                    "content_length": len(content) if content else 0,
                }
            )
            
            return doc_id
            
        except Exception as e:
            raise LanceDBError(f"Failed to add document: {e}")
    
    def search(
        self,
        query: str,
        limit: int = 10,
        filter_category: Optional[str] = None,
        filter_language: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search documents using semantic similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            filter_category: Filter by category (optional)
            filter_language: Filter by language (optional)
            min_score: Minimum similarity score (0.0 - 1.0).
                      If None, uses config value (search.lancedb.min_score)
        
        Returns:
            List of matching documents with scores
        
        Example:
            >>> results = client.search("Germany trip 2025", limit=5)
            >>> for doc in results:
            ...     print(f"{doc['title']} - Score: {doc['_score']:.2f}")
        """
        # Get min_score from config if not specified
        if min_score is None:
            if self._config:
                min_score = self._config.get("search.lancedb.min_score", 0.0)
            else:
                min_score = 0.0
        
        # Generate query embedding (allow empty to return zero vector for safety)
        query_embedding = self._embed_text(query, allow_empty=True)
        
        try:
            table = self.db.open_table(self.table_name)
            
            # Build search query with explicit vector column name
            search_query = table.search(
                query_embedding,
                vector_column_name="vector"
            ).limit(limit * 2)  # Over-fetch to account for empty content filtering
            
            # Apply filters
            filters = []
            if filter_category:
                filters.append(f"category = '{filter_category}'")
            if filter_language:
                filters.append(f"language = '{filter_language}'")
            
            if filters:
                search_query = search_query.where(" AND ".join(filters))
            
            # Execute search
            results = search_query.to_list()
            
            # Format results
            formatted = []
            for row in results:
                # Skip documents with empty content (legacy data protection)
                content = row.get("content", "")
                if not content or not content.strip():
                    continue
                
                # LanceDB returns distance, convert to similarity score
                # Assuming L2 distance, smaller is better
                distance = row.get("_distance", 0)
                score = 1.0 / (1.0 + distance)  # Convert to 0-1 range
                
                if score >= min_score and len(formatted) < limit:
                    formatted.append({
                        "id": row.get("id"),
                        "path": row.get("path"),
                        "title": row.get("title"),
                        "content": content[:500],  # Preview
                        "category": row.get("category"),
                        "language": row.get("language"),
                        "file_type": row.get("file_type"),
                        "created_at": row.get("created_at"),
                        "metadata": json.loads(row.get("metadata", "{}")),
                        "_score": score,
                        "_distance": distance,
                    })
            
            self.logger.info(
                "Search completed",
                metadata={
                    "query": query[:50],
                    "results_count": len(formatted),
                    "limit": limit,
                }
            )
            
            return formatted
            
        except Exception as e:
            raise LanceDBError(f"Search failed: {e}")
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete a document from the index.
        
        Args:
            doc_id: Document ID (SHA256 hash)
        
        Returns:
            True if deleted, False if not found
        """
        try:
            table = self.db.open_table(self.table_name)
            
            # Check if exists using pandas filter
            df = table.to_pandas()
            existing = df[df["id"] == doc_id].to_dict(orient="records")
            
            if not existing:
                return False
            
            table.delete(f"id = '{doc_id}'")
            
            self.logger.info(
                "Document deleted",
                metadata={"id": doc_id}
            )
            
            return True
            
        except Exception as e:
            raise LanceDBError(f"Delete failed: {e}")
    
    def delete_by_path(self, path: str) -> bool:
        """
        Delete a document by its file path.
        
        Args:
            path: Absolute file path
        
        Returns:
            True if deleted, False if not found
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
            table = self.db.open_table(self.table_name)
            # Use pandas filter for non-vector search
            df = table.to_pandas()
            results = df[df["id"] == doc_id].to_dict(orient="records")
            
            if not results:
                return None
            
            row = results[0]
            return {
                "id": row.get("id"),
                "path": row.get("path"),
                "title": row.get("title"),
                "content": row.get("content"),
                "category": row.get("category"),
                "language": row.get("language"),
                "file_type": row.get("file_type"),
                "file_size": row.get("file_size"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "metadata": json.loads(row.get("metadata", "{}")),
            }
            
        except Exception as e:
            raise LanceDBError(f"Get document failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Dict with count, categories, languages, etc.
        """
        try:
            table = self.db.open_table(self.table_name)
            
            # Get all documents using pandas
            df = table.to_pandas()
            all_docs = df.to_dict(orient="records")
            total_count = len(all_docs)
            
            # Aggregate categories and languages
            categories = {}
            languages = {}
            total_size = 0
            
            for doc in all_docs:
                cat = doc.get("category", "unknown")
                lang = doc.get("language", "unknown")
                size = doc.get("file_size", 0)
                
                categories[cat] = categories.get(cat, 0) + 1
                languages[lang] = languages.get(lang, 0) + 1
                total_size += size
            
            if self.dimension is None:
                self.dimension = self._resolve_dimension_from_table()

            return {
                StatsKeys.TOTAL_DOCUMENTS: total_count,
                StatsKeys.CATEGORIES: categories,
                StatsKeys.LANGUAGES: languages,
                StatsKeys.TOTAL_SIZE_BYTES: total_size,
                StatsKeys.TOTAL_SIZE_MB: round(total_size / (1024 * 1024), 2),
                StatsKeys.TABLE_NAME: self.table_name,
                StatsKeys.EMBEDDING_DIMENSION: self.dimension or 0,
                StatsKeys.DB_PATH: str(self.db_path),
            }
            
        except Exception as e:
            raise LanceDBError(f"Get stats failed: {e}")

    def get_all_vector_paths(self) -> set:
        """
        Return the set of all file paths that have vectors in LanceDB.

        Returns an empty set if the table does not exist yet.

        Returns:
            Set of absolute file paths stored in LanceDB

        Raises:
            LanceDBError: If the lookup fails
        """
        try:
            tables_response = self.db.list_tables()
            table_names = (
                tables_response.tables
                if hasattr(tables_response, "tables")
                else list(tables_response)
            )
            if self.table_name not in table_names:
                return set()

            table = self.db.open_table(self.table_name)
            df = table.to_pandas()
            return set(df["path"].dropna().tolist())
        except Exception as e:
            raise LanceDBError(f"Failed to list vector paths: {e}")

    def clear(self) -> int:
        """
        Delete all documents from the index.
        
        Returns:
            Number of documents deleted
        """
        try:
            table = self.db.open_table(self.table_name)
            count = len(table.to_pandas())
            
            # Drop and recreate table
            self.db.drop_table(self.table_name)
            self._ensure_table()
            
            self.logger.warning(
                "Index cleared",
                metadata={"deleted_count": count}
            )
            
            return count
            
        except Exception as e:
            raise LanceDBError(f"Clear failed: {e}")
