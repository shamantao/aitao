"""
Indexation module for AItao.

This module handles:
- Filesystem scanning and file discovery
- Task queue management
- Background worker processing
- Document extraction and preparation
- Document indexing pipeline
- Text chunking for RAG
"""

from src.indexation.scanner import FilesystemScanner
from src.indexation.queue import TaskQueue
from src.indexation.worker import BackgroundWorker
from src.indexation.text_extractor import TextExtractor, extract_text
from src.indexation.indexer import DocumentIndexer, IndexResult, BatchIndexResult, index_file
from src.indexation.interfaces import Chunk, ChunkingConfig, ChunkingResult
from src.indexation.chunker import ChunkingPipeline, chunk_text

__all__ = [
    "FilesystemScanner",
    "TaskQueue",
    "BackgroundWorker",
    "TextExtractor",
    "extract_text",
    "DocumentIndexer",
    "IndexResult",
    "BatchIndexResult",
    "index_file",
    # Chunking
    "Chunk",
    "ChunkingConfig",
    "ChunkingResult",
    "ChunkingPipeline",
    "chunk_text",
]
