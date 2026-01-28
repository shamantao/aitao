"""
Indexation module for AItao.

This module handles:
- Filesystem scanning and file discovery
- Task queue management
- Background worker processing
- Document extraction and preparation
"""

from indexation.scanner import FilesystemScanner
from indexation.queue import TaskQueue
from indexation.worker import BackgroundWorker
from indexation.text_extractor import TextExtractor, extract_text

__all__ = [
    "FilesystemScanner",
    "TaskQueue",
    "BackgroundWorker",
    "TextExtractor",
    "extract_text",
]
