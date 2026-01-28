"""
Indexation module for AItao.

This module handles:
- Filesystem scanning and file discovery
- Task queue management
- Background worker processing
- Document extraction and preparation
- Document indexing pipeline
"""

from indexation.scanner import FilesystemScanner
from indexation.queue import TaskQueue
from indexation.worker import BackgroundWorker
from indexation.text_extractor import TextExtractor, extract_text
from indexation.indexer import DocumentIndexer, IndexResult, BatchIndexResult, index_file

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
]
