"""
Indexation module for AItao.

This module handles:
- Filesystem scanning and file discovery
- Task queue management
- Background worker processing
- Document extraction and preparation
- Document indexing pipeline
- Text chunking for RAG

NOTE: Imports are intentionally NOT eager here.
      Importing this package does NOT load sentence_transformers, lancedb, or
      other heavy ML libraries. Each sub-module must be imported directly:
        from indexation.queue import TaskQueue
        from indexation.worker import BackgroundWorker
      This keeps CLI startup time fast (--help, dashboard, etc.).
"""

# No eager imports — all sub-modules are loaded on demand.
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
    "Chunk",
    "ChunkingConfig",
    "ChunkingResult",
    "ChunkingPipeline",
    "chunk_text",
]
