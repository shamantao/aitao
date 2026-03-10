"""
ChunkStore - Storage and retrieval of document chunks in LanceDB.

This module manages the storage of text chunks in LanceDB for RAG retrieval.
Chunks are stored separately from full documents to enable fine-grained
semantic search at the chunk level.

Responsibilities:
- Store chunks with embeddings in LanceDB
- Search chunks by semantic similarity
- Delete chunks when document is re-indexed
- Manage the chunks table schema
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lancedb
import pyarrow as pa

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from src.indexation.interfaces import Chunk, ChunkingConfig

logger = logging.getLogger(__name__)


class ChunkStoreError(Exception):
    """Base exception for ChunkStore operations."""
    pass


class ChunkStore:
    """
    Storage backend for document chunks in LanceDB.
    
    Chunks are stored in a separate table from documents to enable
    efficient semantic search at the chunk level. Each chunk has its
    own embedding vector.
    
    Schema:
        - chunk_id: str (primary key) - "{doc_sha256}_{chunk_index:05d}"
        - doc_id: str - SHA256 of parent document
        - path: str - Source file path
        - title: str - Document title
        - content: str - Chunk text content
        - chunk_index: int - Position in document
        - total_chunks: int - Total chunks in document
        - offset_start: int - Character offset start
        - offset_end: int - Character offset end
        - metadata: str - JSON metadata
        - created_at: str - ISO timestamp
        - vector: list[float] - Embedding vector
    
    Example:
        ```python
        store = ChunkStore(db_path="/path/to/lancedb")
        
        # Add chunks
        store.add_chunks(chunks)
        
        # Search
        results = store.search("query text", limit=5)
        for chunk, score in results:
            print(f"{chunk.chunk_id}: {score:.3f}")
        ```
    """
    
    TABLE_NAME = "chunks"
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ):
        """
        Initialize ChunkStore.
        
        Args:
            db_path: Path to LanceDB directory. If None, uses config.
            embedding_model: Model name for embeddings.
            config: ChunkingConfig with embedding_model setting.
        
        Raises:
            ChunkStoreError: If initialization fails
        """
        self.config = config or ChunkingConfig()
        
        # Determine DB path
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Try to get from global config
            try:
                from src.core.config import get_config
                cfg = get_config()
                vector_db_dir = cfg.get("paths.vector_db_dir")
                if vector_db_dir:
                    self.db_path = Path(vector_db_dir)
                else:
                    storage_root = cfg.get("paths.storage_root")
                    self.db_path = Path(storage_root) / "lancedb" if storage_root else None
            except Exception:
                self.db_path = None
        
        if not self.db_path:
            raise ChunkStoreError("No LanceDB path configured")
        
        # Load embedding model
        model_name = embedding_model or self.config.embedding_model
        logger.info(f"Loading embedding model: {model_name}")
        
        if SentenceTransformer is None:
            raise ChunkStoreError("sentence-transformers not installed")
        
        try:
            self._embedding_model = SentenceTransformer(model_name)
            self.dimension = self._embedding_model.get_sentence_embedding_dimension()
        except Exception as e:
            raise ChunkStoreError(f"Failed to load embedding model: {e}")
        
        # Connect to LanceDB
        logger.info(f"Connecting to LanceDB: {self.db_path}")
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
            self.db = lancedb.connect(str(self.db_path))
        except Exception as e:
            raise ChunkStoreError(f"Failed to connect to LanceDB: {e}")
        
        # Ensure chunks table exists
        self._ensure_table()
        
        logger.info(
            f"ChunkStore initialized: table={self.TABLE_NAME}, "
            f"dimension={self.dimension}"
        )
    
    def _get_schema(self) -> pa.Schema:
        """Generate PyArrow schema for chunks table."""
        return pa.schema([
            pa.field("chunk_id", pa.string()),
            pa.field("doc_id", pa.string()),
            pa.field("path", pa.string()),
            pa.field("title", pa.string()),
            pa.field("content", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("total_chunks", pa.int32()),
            pa.field("offset_start", pa.int32()),
            pa.field("offset_end", pa.int32()),
            pa.field("metadata", pa.string()),
            pa.field("created_at", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self.dimension)),
        ])
    
    def _ensure_table(self) -> None:
        """Create chunks table if it doesn't exist."""
        try:
            # list_tables() may return strings or table objects
            tables = self.db.list_tables()
            table_names = [str(t) for t in tables]
            
            if self.TABLE_NAME not in table_names:
                self.db.create_table(
                    self.TABLE_NAME,
                    schema=self._get_schema(),
                    mode="create"
                )
                logger.info(f"Created table: {self.TABLE_NAME}")
            else:
                logger.debug(f"Table already exists: {self.TABLE_NAME}")
        except Exception as e:
            # Handle race condition: table created between check and create
            if "already exists" in str(e).lower():
                logger.debug(f"Table {self.TABLE_NAME} already exists (race)")
            else:
                raise ChunkStoreError(f"Failed to ensure table: {e}")
    
    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        embedding = self._embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _chunk_to_record(self, chunk: Chunk) -> Dict[str, Any]:
        """Convert Chunk to database record."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Generate embedding if not present
        if chunk.embedding is None:
            embedding = self._embed_text(chunk.content)
        else:
            embedding = chunk.embedding
        
        return {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "path": chunk.path,
            "title": chunk.title,
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "offset_start": chunk.offset_start,
            "offset_end": chunk.offset_end,
            "metadata": json.dumps(chunk.metadata),
            "created_at": now,
            "vector": embedding,
        }
    
    def _record_to_chunk(self, record: Dict[str, Any], score: float = 0.0) -> Chunk:
        """Convert database record to Chunk."""
        metadata = record.get("metadata", "{}")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        
        return Chunk(
            chunk_id=record["chunk_id"],
            doc_id=record["doc_id"],
            path=record["path"],
            title=record["title"],
            content=record["content"],
            chunk_index=record["chunk_index"],
            total_chunks=record["total_chunks"],
            offset_start=record["offset_start"],
            offset_end=record["offset_end"],
            metadata=metadata,
            embedding=record.get("vector"),
            created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
            if record.get("created_at") else datetime.now(),
        )
    
    def add_chunks(self, chunks: List[Chunk]) -> int:
        """
        Add multiple chunks to the store.
        
        Args:
            chunks: List of Chunk objects to store
            
        Returns:
            Number of chunks added
            
        Raises:
            ChunkStoreError: If add operation fails
        """
        if not chunks:
            return 0
        
        try:
            table = self.db.open_table(self.TABLE_NAME)
            
            # Convert chunks to records
            records = [self._chunk_to_record(chunk) for chunk in chunks]
            
            # Add to table
            table.add(records)
            
            logger.info(f"Added {len(records)} chunks for doc_id={chunks[0].doc_id}")
            return len(records)
            
        except Exception as e:
            raise ChunkStoreError(f"Failed to add chunks: {e}")
    
    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            doc_id: SHA256 of the document
            
        Returns:
            Number of chunks deleted (estimated)
        """
        try:
            table = self.db.open_table(self.TABLE_NAME)
            
            # Count before deletion
            pre_count = table.count_rows()
            
            # Delete chunks for this document
            table.delete(f'doc_id = "{doc_id}"')
            
            # Count after deletion
            post_count = table.count_rows()
            deleted = pre_count - post_count
            
            if deleted > 0:
                logger.info(f"Deleted {deleted} chunks for doc_id={doc_id[:16]}...")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for doc_id={doc_id}: {e}")
            return 0
    
    def search(
        self,
        query: str,
        limit: int = 10,
        doc_id: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for relevant chunks.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            doc_id: Optional filter by document ID
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of (Chunk, score) tuples sorted by relevance
        """
        try:
            table = self.db.open_table(self.TABLE_NAME)
            
            # Generate query embedding
            query_vector = self._embed_text(query)
            
            # Build search query
            search_builder = table.search(query_vector).limit(limit)
            
            # Add filter if doc_id specified
            if doc_id:
                search_builder = search_builder.where(f'doc_id = "{doc_id}"')
            
            # Execute search
            results = search_builder.to_list()
            
            # Convert to Chunk objects with scores
            chunks_with_scores = []
            for record in results:
                # LanceDB returns _distance (L2 or cosine depending on config)
                # For cosine distance: range is [0, 2], so similarity = 1 - distance/2
                # For L2 distance: we use inverse formula
                distance = record.get("_distance", 0.0)
                
                # Convert distance to similarity score (0-1)
                # Assuming cosine distance (range 0-2)
                if distance <= 2.0:
                    score = max(0.0, 1.0 - distance / 2.0)
                else:
                    # L2 distance - use exponential decay
                    score = max(0.0, 1.0 / (1.0 + distance))
                
                if score >= min_score:
                    chunk = self._record_to_chunk(record, score)
                    chunks_with_scores.append((chunk, score))
            
            logger.debug(
                f"Search returned {len(chunks_with_scores)} chunks "
                f"for query: {query[:50]}..."
            )
            
            return chunks_with_scores
            
        except Exception as e:
            logger.error(f"Chunk search failed: {e}")
            return []
    
    def get_by_chunk_id(self, chunk_id: str) -> Optional[Chunk]:
        """
        Get a specific chunk by ID.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk object or None if not found
        """
        try:
            table = self.db.open_table(self.TABLE_NAME)
            results = table.search().where(f'chunk_id = "{chunk_id}"').limit(1).to_list()
            
            if results:
                return self._record_to_chunk(results[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None
    
    def get_chunks_by_doc_id(self, doc_id: str) -> List[Chunk]:
        """
        Get all chunks for a document, ordered by chunk_index.
        
        Args:
            doc_id: SHA256 of the document
            
        Returns:
            List of Chunk objects in order
        """
        try:
            table = self.db.open_table(self.TABLE_NAME)
            results = table.search().where(f'doc_id = "{doc_id}"').limit(1000).to_list()
            
            chunks = [self._record_to_chunk(r) for r in results]
            # Sort by chunk_index
            chunks.sort(key=lambda c: c.chunk_index)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks for doc {doc_id}: {e}")
            return []
    
    def count_chunks(self, doc_id: Optional[str] = None) -> int:
        """
        Count chunks in the store.
        
        Args:
            doc_id: Optional filter by document ID
            
        Returns:
            Number of chunks
        """
        try:
            table = self.db.open_table(self.TABLE_NAME)
            
            if doc_id:
                # Filter and count
                results = table.search().where(f'doc_id = "{doc_id}"').limit(10000).to_list()
                return len(results)
            else:
                return table.count_rows()
                
        except Exception as e:
            logger.error(f"Failed to count chunks: {e}")
            return 0
    
    def stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with chunk count, unique documents, etc.
        """
        try:
            table = self.db.open_table(self.TABLE_NAME)
            total_chunks = table.count_rows()
            
            # Get unique doc_ids
            all_records = table.to_pandas() if total_chunks < 100000 else None
            unique_docs = len(all_records["doc_id"].unique()) if all_records is not None else -1
            
            return {
                "total_chunks": total_chunks,
                "unique_documents": unique_docs,
                "embedding_dimension": self.dimension,
                "table_name": self.TABLE_NAME,
                "db_path": str(self.db_path),
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
