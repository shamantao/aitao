"""
Indexation module for AItao.

This module handles:
- Filesystem scanning and file discovery
- Task queue management
- Background worker processing
- Document extraction and preparation
"""

from indexation.scanner import FilesystemScanner

__all__ = ["FilesystemScanner"]
