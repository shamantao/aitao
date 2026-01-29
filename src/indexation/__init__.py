"""
Indexation module for AItao.

This module handles:
- Filesystem scanning and file discovery
- Task queue management
- Background worker processing
- Document extraction and preparation
- Document indexing pipeline
"""

from src.indexation.scanner import FilesystemScanner
from src.indexation.queue import TaskQueue
from src.indexation.worker import BackgroundWorker
from src.indexation.text_extractor import TextExtractor, extract_text
from src.indexation.indexer import DocumentIndexer, IndexResult, BatchIndexResult, index_file

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
