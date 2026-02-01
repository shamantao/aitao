"""
ChunkingPipeline - Split documents into chunks for RAG retrieval.

This module handles the segmentation of documents into smaller chunks
that can be embedded and searched individually. This is CRITICAL for
RAG quality - without chunking, the LLM only sees a tiny fraction of
large documents.

Problem solved:
- context_max_tokens: 2000 = only 0.7% of a typical 285K token PDF
- The LLM receives a random excerpt, not the relevant section
- With chunking, we search chunks and return the RELEVANT parts

Responsibilities:
- Split text into overlapping chunks of ~512 tokens
- Respect sentence boundaries when possible
- Generate unique chunk IDs
- Track character offsets for highlighting
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from src.indexation.interfaces import Chunk, ChunkingConfig, ChunkingResult

logger = logging.getLogger(__name__)

# Approximate characters per token (conservative estimate)
# Chinese/Japanese: ~1.5 chars/token, English: ~4 chars/token
# We use 3 as a balanced estimate for multilingual content
CHARS_PER_TOKEN = 3


class ChunkingPipeline:
    """
    Pipeline for splitting documents into searchable chunks.
    
    The chunking strategy uses overlapping windows to ensure that
    relevant content isn't split across chunk boundaries. Chunks
    overlap by ~50 tokens to maintain context.
    
    Example:
        ```python
        pipeline = ChunkingPipeline(config)
        result = pipeline.chunk_document(
            text="Long document text...",
            doc_id="abc123",
            path="/path/to/doc.pdf",
            title="My Document"
        )
        for chunk in result.chunks:
            print(f"Chunk {chunk.chunk_index}: {len(chunk.content)} chars")
        ```
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize the chunking pipeline.
        
        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkingConfig()
        
        # Convert token sizes to character sizes
        self.chunk_size_chars = self.config.chunk_size * CHARS_PER_TOKEN
        self.overlap_chars = self.config.chunk_overlap * CHARS_PER_TOKEN
        self.min_chunk_chars = self.config.min_chunk_size * CHARS_PER_TOKEN
        self.max_chunk_chars = self.config.max_chunk_size * CHARS_PER_TOKEN
        
        logger.debug(
            f"ChunkingPipeline initialized: {self.config.chunk_size} tokens "
            f"({self.chunk_size_chars} chars), overlap={self.config.chunk_overlap}"
        )
    
    def chunk_document(
        self,
        text: str,
        doc_id: str,
        path: str,
        title: str,
        metadata: Optional[dict] = None,
    ) -> ChunkingResult:
        """
        Split a document into chunks.
        
        Args:
            text: Full document text
            doc_id: SHA256 hash of the document
            path: File path of the source
            title: Document title
            metadata: Optional metadata to attach to all chunks
            
        Returns:
            ChunkingResult with list of Chunk objects
        """
        if not text or not text.strip():
            logger.warning(f"Empty text for document {path}")
            return ChunkingResult(
                doc_id=doc_id,
                path=path,
                chunks=[],
                total_tokens=0,
                success=False,
                error="Empty document text",
            )
        
        try:
            # Normalize whitespace
            text = self._normalize_text(text)
            
            # Split into chunks
            raw_chunks = self._split_text(text)
            
            # Create Chunk objects
            chunks = []
            total_chunks = len(raw_chunks)
            
            for idx, (content, offset_start, offset_end) in enumerate(raw_chunks):
                chunk = Chunk.create(
                    doc_id=doc_id,
                    path=path,
                    title=title,
                    content=content,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                    offset_start=offset_start,
                    offset_end=offset_end,
                    metadata=metadata,
                )
                chunks.append(chunk)
            
            # Estimate total tokens
            total_tokens = len(text) // CHARS_PER_TOKEN
            
            logger.info(
                f"Chunked {path}: {total_chunks} chunks, "
                f"~{total_tokens} tokens"
            )
            
            return ChunkingResult(
                doc_id=doc_id,
                path=path,
                chunks=chunks,
                total_tokens=total_tokens,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Chunking failed for {path}: {e}")
            return ChunkingResult(
                doc_id=doc_id,
                path=path,
                chunks=[],
                total_tokens=0,
                success=False,
                error=str(e),
            )
    
    def chunk_text(
        self,
        text: str,
        doc_id: str,
    ) -> List[Chunk]:
        """
        Simple interface to chunk text without full metadata.
        
        Args:
            text: Text to chunk
            doc_id: Document identifier
            
        Returns:
            List of Chunk objects
        """
        result = self.chunk_document(
            text=text,
            doc_id=doc_id,
            path="",
            title="",
        )
        return result.chunks
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for chunking.
        
        - Replace multiple newlines with double newline
        - Replace multiple spaces with single space
        - Strip leading/trailing whitespace
        """
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Collapse multiple newlines (but keep paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)
        
        return text.strip()
    
    def _split_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into overlapping chunks.
        
        Returns:
            List of (chunk_content, offset_start, offset_end) tuples
        """
        if len(text) <= self.chunk_size_chars:
            # Document fits in single chunk
            return [(text, 0, len(text))]
        
        chunks = []
        offset = 0
        
        while offset < len(text):
            # Calculate chunk end position
            chunk_end = min(offset + self.chunk_size_chars, len(text))
            
            # If not at the end, try to find a good break point
            if chunk_end < len(text) and self.config.split_on_sentences:
                chunk_end = self._find_break_point(text, offset, chunk_end)
            
            # Extract chunk content
            chunk_content = text[offset:chunk_end].strip()
            
            # Only add non-empty chunks above minimum size
            if chunk_content and len(chunk_content) >= self.min_chunk_chars:
                chunks.append((chunk_content, offset, chunk_end))
            elif chunk_content:
                # Small final chunk - append to previous if possible
                if chunks:
                    prev_content, prev_start, prev_end = chunks[-1]
                    merged = prev_content + " " + chunk_content
                    if len(merged) <= self.max_chunk_chars:
                        chunks[-1] = (merged, prev_start, chunk_end)
                    else:
                        # Can't merge, add as small chunk anyway
                        chunks.append((chunk_content, offset, chunk_end))
                else:
                    chunks.append((chunk_content, offset, chunk_end))
            
            # Move to next chunk with overlap
            if chunk_end >= len(text):
                break
            
            # Calculate next offset (current end minus overlap)
            offset = chunk_end - self.overlap_chars
            
            # Ensure we make progress
            if offset <= chunks[-1][1] if chunks else 0:
                offset = chunk_end
        
        return chunks
    
    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """
        Find a good break point near the end position.
        
        Tries to break on (in order of preference):
        1. Paragraph break (double newline)
        2. Sentence end (. ! ?)
        3. Clause break (, ; :)
        4. Word boundary (space)
        
        Args:
            text: Full text
            start: Chunk start position
            end: Target end position
            
        Returns:
            Adjusted end position
        """
        # Search window: last 20% of chunk
        search_start = end - int(self.chunk_size_chars * 0.2)
        search_start = max(search_start, start)
        window = text[search_start:end]
        
        # Try paragraph break
        para_break = window.rfind("\n\n")
        if para_break > 0:
            return search_start + para_break + 2
        
        # Try sentence end
        for pattern in [". ", "。", "! ", "? ", "！", "？"]:
            sent_end = window.rfind(pattern)
            if sent_end > 0:
                return search_start + sent_end + len(pattern)
        
        # Try newline
        newline = window.rfind("\n")
        if newline > 0:
            return search_start + newline + 1
        
        # Try clause break
        for pattern in [", ", "、", "; ", ": "]:
            clause_end = window.rfind(pattern)
            if clause_end > 0:
                return search_start + clause_end + len(pattern)
        
        # Try word boundary
        space = window.rfind(" ")
        if space > 0:
            return search_start + space + 1
        
        # No good break point, use original end
        return end
    
    @staticmethod
    def compute_doc_id(content: str) -> str:
        """
        Compute SHA256 hash for document ID.
        
        Args:
            content: Document content
            
        Returns:
            Hex string of SHA256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // CHARS_PER_TOKEN


# Convenience function for simple usage
def chunk_text(
    text: str,
    doc_id: Optional[str] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[Chunk]:
    """
    Convenience function to chunk text with default settings.
    
    Args:
        text: Text to chunk
        doc_id: Optional document ID (computed from content if not provided)
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks in tokens
        
    Returns:
        List of Chunk objects
    """
    if doc_id is None:
        doc_id = ChunkingPipeline.compute_doc_id(text)
    
    config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    pipeline = ChunkingPipeline(config)
    return pipeline.chunk_text(text, doc_id)
