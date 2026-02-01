"""
Interfaces and data classes for the indexation module.

This module defines the core data structures used throughout the indexation
pipeline, including chunks for RAG, document metadata, and extraction results.

Responsibilities:
- Define Chunk dataclass for text segmentation
- Define document-level interfaces
- Provide type hints for the entire indexation module
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib


@dataclass
class Chunk:
    """
    A text chunk for RAG retrieval.
    
    Documents are split into chunks to enable precise retrieval.
    Each chunk contains a portion of the document text with context
    about its position and parent document.
    
    Attributes:
        chunk_id: Unique identifier "{doc_sha256}_{chunk_index}"
        doc_id: SHA256 hash of the parent document
        path: File path of the source document
        title: Document title (filename or extracted)
        content: Text content of this chunk (target: 512 tokens)
        chunk_index: Position in the document (0-based)
        total_chunks: Total number of chunks in the document
        offset_start: Character offset where this chunk starts
        offset_end: Character offset where this chunk ends
        metadata: Additional metadata (category, language, etc.)
        embedding: Vector embedding (filled by embedding model)
        created_at: Timestamp when chunk was created
    """
    
    chunk_id: str
    doc_id: str
    path: str
    title: str
    content: str
    chunk_index: int
    total_chunks: int
    offset_start: int
    offset_end: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(
        cls,
        doc_id: str,
        path: str,
        title: str,
        content: str,
        chunk_index: int,
        total_chunks: int,
        offset_start: int,
        offset_end: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Chunk":
        """
        Factory method to create a Chunk with auto-generated chunk_id.
        
        Args:
            doc_id: SHA256 of the parent document
            path: File path of the source
            title: Document title
            content: Chunk text content
            chunk_index: Position in document
            total_chunks: Total chunks in document
            offset_start: Character offset start
            offset_end: Character offset end
            metadata: Optional additional metadata
            
        Returns:
            New Chunk instance with generated chunk_id
        """
        chunk_id = f"{doc_id}_{chunk_index:05d}"
        return cls(
            chunk_id=chunk_id,
            doc_id=doc_id,
            path=path,
            title=title,
            content=content,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            offset_start=offset_start,
            offset_end=offset_end,
            metadata=metadata or {},
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "path": self.path,
            "title": self.title,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create chunk from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
            
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            path=data["path"],
            title=data["title"],
            content=data["content"],
            chunk_index=data["chunk_index"],
            total_chunks=data["total_chunks"],
            offset_start=data["offset_start"],
            offset_end=data["offset_end"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            created_at=created_at,
        )
    
    def __len__(self) -> int:
        """Return content length in characters."""
        return len(self.content)
    
    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Chunk({self.chunk_id}, {len(self.content)} chars, '{preview}')"


@dataclass
class ChunkingConfig:
    """
    Configuration for the chunking pipeline.
    
    Attributes:
        chunk_size: Target size in tokens (default: 512)
        chunk_overlap: Overlap between chunks in tokens (default: 50)
        min_chunk_size: Minimum chunk size in tokens (default: 100)
        max_chunk_size: Maximum chunk size in tokens (default: 1024)
        split_on_sentences: Try to split on sentence boundaries
        embedding_model: Model for embeddings (default: BAAI/bge-m3)
    """
    
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 1024
    split_on_sentences: bool = True
    embedding_model: str = "BAAI/bge-m3"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkingConfig":
        """Create config from dictionary (e.g., from config.yaml)."""
        return cls(
            chunk_size=data.get("chunk_size", 512),
            chunk_overlap=data.get("chunk_overlap", 50),
            min_chunk_size=data.get("min_chunk_size", 100),
            max_chunk_size=data.get("max_chunk_size", 1024),
            split_on_sentences=data.get("split_on_sentences", True),
            embedding_model=data.get("embedding_model", "BAAI/bge-m3"),
        )


@dataclass
class ChunkingResult:
    """
    Result of chunking a document.
    
    Attributes:
        doc_id: SHA256 of the source document
        path: File path of the source
        chunks: List of generated chunks
        total_tokens: Estimated total tokens in document
        success: Whether chunking succeeded
        error: Error message if failed
    """
    
    doc_id: str
    path: str
    chunks: List[Chunk]
    total_tokens: int = 0
    success: bool = True
    error: Optional[str] = None
    
    @property
    def chunk_count(self) -> int:
        """Number of chunks generated."""
        return len(self.chunks)
    
    def __repr__(self) -> str:
        status = "✓" if self.success else f"✗ {self.error}"
        return f"ChunkingResult({self.path}, {self.chunk_count} chunks, {status})"
