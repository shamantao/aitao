"""
DocumentIndexer - Orchestrate document indexing pipeline.

This module provides the main indexing workflow:
1. Extract text from document (TextExtractor)
2. Generate embeddings and index in LanceDB (semantic search)
3. Index in Meilisearch (full-text search)
4. Handle deduplication via SHA256
5. Track indexing status and errors

Responsibilities:
- Coordinate extraction and indexing
- Handle deduplication
- Provide batch indexing capabilities
- Log all operations
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import logging

from src.indexation.text_extractor import TextExtractor, ExtractionResult
from search.lancedb_client import LanceDBClient, LanceDBError
from search.meilisearch_client import MeilisearchClient, MeilisearchError

try:
    from core.logger import get_logger
    from core.config import ConfigManager
except ImportError:
    get_logger = lambda name: logging.getLogger(name)
    ConfigManager = None


@dataclass
class IndexResult:
    """Result of indexing a single document."""
    
    path: str
    """Path to the indexed document."""
    
    doc_id: str
    """SHA256-based document ID."""
    
    success: bool = True
    """Whether indexing was successful."""
    
    lancedb_indexed: bool = False
    """Whether document was indexed in LanceDB."""
    
    meilisearch_indexed: bool = False
    """Whether document was indexed in Meilisearch."""
    
    error: Optional[str] = None
    """Error message if indexing failed."""
    
    extraction_time_ms: float = 0
    """Time taken for text extraction in milliseconds."""
    
    indexing_time_ms: float = 0
    """Time taken for indexing in milliseconds."""
    
    word_count: int = 0
    """Word count of extracted text."""
    
    language: Optional[str] = None
    """Detected language."""
    
    @property
    def total_time_ms(self) -> float:
        """Total processing time in milliseconds."""
        return self.extraction_time_ms + self.indexing_time_ms


@dataclass
class BatchIndexResult:
    """Result of batch indexing multiple documents."""
    
    total: int = 0
    """Total number of documents processed."""
    
    successful: int = 0
    """Number of successfully indexed documents."""
    
    failed: int = 0
    """Number of failed documents."""
    
    skipped: int = 0
    """Number of skipped documents (already indexed)."""
    
    results: List[IndexResult] = field(default_factory=list)
    """Individual results for each document."""
    
    total_time_ms: float = 0
    """Total processing time in milliseconds."""
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100


class DocumentIndexer:
    """
    Main document indexing orchestrator.
    
    Coordinates the full indexing pipeline:
    1. Extract text using TextExtractor
    2. Generate embeddings and store in LanceDB
    3. Index full-text in Meilisearch
    4. Handle deduplication and updates
    
    Example:
        indexer = DocumentIndexer()
        result = indexer.index_file("/path/to/document.pdf")
        if result.success:
            print(f"Indexed: {result.doc_id}")
        
        # Batch indexing
        batch_result = indexer.index_files(["/path/to/doc1.pdf", "/path/to/doc2.docx"])
        print(f"Indexed {batch_result.successful}/{batch_result.total} documents")
    """
    
    def __init__(
        self,
        lancedb_client: Optional[LanceDBClient] = None,
        meilisearch_client: Optional[MeilisearchClient] = None,
        text_extractor: Optional[TextExtractor] = None,
        config: Optional[ConfigManager] = None,
        skip_lancedb: bool = False,
        skip_meilisearch: bool = False,
    ):
        """
        Initialize the document indexer.
        
        Args:
            lancedb_client: LanceDB client instance. Created if None.
            meilisearch_client: Meilisearch client instance. Created if None.
            text_extractor: TextExtractor instance. Created if None.
            config: ConfigManager instance.
            skip_lancedb: Skip LanceDB indexing (for testing).
            skip_meilisearch: Skip Meilisearch indexing (for testing).
        """
        self.logger = get_logger("indexer")
        self.config = config
        
        # Initialize components
        self.text_extractor = text_extractor or TextExtractor()
        
        self.skip_lancedb = skip_lancedb
        self.skip_meilisearch = skip_meilisearch
        
        # Lazy initialization for search clients
        self._lancedb_client = lancedb_client
        self._meilisearch_client = meilisearch_client
    
    @property
    def lancedb(self) -> Optional[LanceDBClient]:
        """Get or create LanceDB client."""
        if self.skip_lancedb:
            return None
        if self._lancedb_client is None:
            try:
                self._lancedb_client = LanceDBClient(config=self.config)
            except Exception as e:
                self.logger.error(f"Failed to initialize LanceDB: {e}")
                return None
        return self._lancedb_client
    
    @property
    def meilisearch(self) -> Optional[MeilisearchClient]:
        """Get or create Meilisearch client."""
        if self.skip_meilisearch:
            return None
        if self._meilisearch_client is None:
            try:
                self._meilisearch_client = MeilisearchClient(config=self.config)
            except Exception as e:
                self.logger.error(f"Failed to initialize Meilisearch: {e}")
                return None
        return self._meilisearch_client
    
    def _generate_id(self, path: str) -> str:
        """Generate document ID from path using SHA256."""
        return hashlib.sha256(path.encode()).hexdigest()
    
    def _get_title(self, path: Path, extraction_result: ExtractionResult) -> str:
        """Extract or generate document title."""
        # Check if title is in metadata
        title = extraction_result.metadata.get("title")
        if title:
            return str(title)
        
        # Use filename without extension
        return path.stem
    
    def _get_category(self, path: Path) -> str:
        """Determine document category from path or extension."""
        ext = path.suffix.lower()
        
        # Document types
        if ext in {".pdf", ".doc", ".docx", ".odt", ".rtf"}:
            return "document"
        
        # Spreadsheets
        if ext in {".xls", ".xlsx", ".ods", ".csv"}:
            return "spreadsheet"
        
        # Presentations
        if ext in {".ppt", ".pptx", ".odp"}:
            return "presentation"
        
        # Images
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}:
            return "image"
        
        # Code
        if ext in {".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs"}:
            return "code"
        
        # Markdown/text
        if ext in {".md", ".markdown", ".txt", ".rst"}:
            return "text"
        
        # Config/data
        if ext in {".json", ".yaml", ".yml", ".toml", ".xml"}:
            return "config"
        
        # Web
        if ext in {".html", ".htm", ".css"}:
            return "web"
        
        return "other"
    
    def index_file(
        self,
        file_path: str | Path,
        force: bool = False,
    ) -> IndexResult:
        """
        Index a single file.
        
        Args:
            file_path: Path to the file to index.
            force: If True, re-index even if document exists.
        
        Returns:
            IndexResult with details of the indexing operation.
        """
        import time
        
        path = Path(file_path)
        doc_id = self._generate_id(str(path))
        
        # Check if file exists
        if not path.exists():
            return IndexResult(
                path=str(path),
                doc_id=doc_id,
                success=False,
                error=f"File not found: {path}"
            )
        
        if not path.is_file():
            return IndexResult(
                path=str(path),
                doc_id=doc_id,
                success=False,
                error=f"Not a file: {path}"
            )
        
        # Check if already indexed (unless force)
        if not force:
            if self._is_already_indexed(doc_id):
                return IndexResult(
                    path=str(path),
                    doc_id=doc_id,
                    success=True,
                    lancedb_indexed=True,
                    meilisearch_indexed=True,
                    error="Already indexed (use force=True to re-index)"
                )
        
        # Step 1: Extract text
        extract_start = time.perf_counter()
        
        extraction = self.text_extractor.extract(path)
        
        extract_time = (time.perf_counter() - extract_start) * 1000
        
        if not extraction.success:
            return IndexResult(
                path=str(path),
                doc_id=doc_id,
                success=False,
                error=f"Extraction failed: {extraction.error}",
                extraction_time_ms=extract_time
            )
        
        # Step 2: Prepare document data
        title = self._get_title(path, extraction)
        category = self._get_category(path)
        language = extraction.language or "unknown"
        file_type = path.suffix.lower()
        file_size = path.stat().st_size
        word_count = extraction.word_count
        
        # Additional metadata
        metadata = {
            "mtime": path.stat().st_mtime,
            "pages": extraction.pages,
            "line_count": extraction.metadata.get("line_count"),
            "encoding": extraction.metadata.get("encoding"),
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        # Step 3: Index in both databases
        index_start = time.perf_counter()
        
        lancedb_ok = False
        meilisearch_ok = False
        errors = []
        
        # Index in LanceDB
        if self.lancedb:
            try:
                self.lancedb.add_document(
                    path=str(path),
                    title=title,
                    content=extraction.text,
                    category=category,
                    language=language,
                    file_type=file_type,
                    file_size=file_size,
                    metadata=metadata,
                )
                lancedb_ok = True
                self.logger.debug(f"LanceDB indexed: {path.name}")
            except LanceDBError as e:
                errors.append(f"LanceDB: {e}")
                self.logger.error(f"LanceDB indexing failed for {path}: {e}")
        
        # Index in Meilisearch
        if self.meilisearch:
            try:
                self.meilisearch.add_document(
                    path=str(path),
                    title=title,
                    content=extraction.text,
                    category=category,
                    language=language,
                    file_type=file_type,
                    file_size=file_size,
                    metadata=metadata,
                )
                meilisearch_ok = True
                self.logger.debug(f"Meilisearch indexed: {path.name}")
            except MeilisearchError as e:
                errors.append(f"Meilisearch: {e}")
                self.logger.error(f"Meilisearch indexing failed for {path}: {e}")
        
        index_time = (time.perf_counter() - index_start) * 1000
        
        # Determine overall success
        success = (lancedb_ok or self.skip_lancedb) and (meilisearch_ok or self.skip_meilisearch)
        
        return IndexResult(
            path=str(path),
            doc_id=doc_id,
            success=success,
            lancedb_indexed=lancedb_ok,
            meilisearch_indexed=meilisearch_ok,
            error="; ".join(errors) if errors else None,
            extraction_time_ms=extract_time,
            indexing_time_ms=index_time,
            word_count=word_count,
            language=language,
        )
    
    def _is_already_indexed(self, doc_id: str) -> bool:
        """Check if document is already indexed."""
        # Check Meilisearch first (faster)
        if self.meilisearch:
            try:
                doc = self.meilisearch.get_document(doc_id)
                if doc:
                    return True
            except Exception:
                pass
        
        # Check LanceDB
        if self.lancedb:
            try:
                doc = self.lancedb.get_document(doc_id)
                if doc:
                    return True
            except Exception:
                pass
        
        return False
    
    def index_files(
        self,
        file_paths: List[str | Path],
        force: bool = False,
        on_progress: Optional[callable] = None,
    ) -> BatchIndexResult:
        """
        Index multiple files.
        
        Args:
            file_paths: List of file paths to index.
            force: If True, re-index even if documents exist.
            on_progress: Optional callback(current, total, result) for progress.
        
        Returns:
            BatchIndexResult with summary and individual results.
        """
        import time
        
        batch_start = time.perf_counter()
        
        result = BatchIndexResult(total=len(file_paths))
        
        for i, file_path in enumerate(file_paths):
            index_result = self.index_file(file_path, force=force)
            result.results.append(index_result)
            
            if index_result.success:
                if index_result.error and "Already indexed" in index_result.error:
                    result.skipped += 1
                else:
                    result.successful += 1
            else:
                result.failed += 1
            
            if on_progress:
                on_progress(i + 1, len(file_paths), index_result)
        
        result.total_time_ms = (time.perf_counter() - batch_start) * 1000
        
        self.logger.info(
            f"Batch indexing complete: {result.successful} indexed, "
            f"{result.skipped} skipped, {result.failed} failed"
        )
        
        return result
    
    def index_directory(
        self,
        directory: str | Path,
        recursive: bool = True,
        force: bool = False,
        on_progress: Optional[callable] = None,
    ) -> BatchIndexResult:
        """
        Index all supported files in a directory.
        
        Args:
            directory: Path to directory to scan.
            recursive: If True, scan subdirectories.
            force: If True, re-index existing documents.
            on_progress: Optional progress callback.
        
        Returns:
            BatchIndexResult with summary and individual results.
        """
        dir_path = Path(directory)
        
        if not dir_path.exists() or not dir_path.is_dir():
            return BatchIndexResult(
                total=0,
                results=[IndexResult(
                    path=str(dir_path),
                    doc_id="",
                    success=False,
                    error=f"Directory not found: {dir_path}"
                )]
            )
        
        # Find all supported files
        supported = self.text_extractor.get_supported_extensions()
        
        if recursive:
            files = [f for f in dir_path.rglob("*") if f.is_file() and f.suffix.lower() in supported]
        else:
            files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in supported]
        
        return self.index_files(files, force=force, on_progress=on_progress)
    
    def delete_document(self, file_path: str | Path) -> Tuple[bool, str]:
        """
        Delete a document from both indexes.
        
        Args:
            file_path: Path of the document to delete.
        
        Returns:
            Tuple of (success, message).
        """
        path = str(file_path)
        doc_id = self._generate_id(path)
        
        lancedb_ok = True
        meilisearch_ok = True
        errors = []
        
        if self.lancedb:
            try:
                self.lancedb.delete(doc_id)
            except Exception as e:
                lancedb_ok = False
                errors.append(f"LanceDB: {e}")
        
        if self.meilisearch:
            try:
                self.meilisearch.delete(doc_id)
            except Exception as e:
                meilisearch_ok = False
                errors.append(f"Meilisearch: {e}")
        
        if lancedb_ok and meilisearch_ok:
            return True, f"Deleted document: {doc_id}"
        else:
            return False, "; ".join(errors)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics from both databases."""
        stats = {
            "lancedb": None,
            "meilisearch": None,
        }
        
        if self.lancedb:
            try:
                stats["lancedb"] = self.lancedb.get_stats()
            except Exception as e:
                stats["lancedb"] = {"error": str(e)}
        
        if self.meilisearch:
            try:
                stats["meilisearch"] = self.meilisearch.get_stats()
            except Exception as e:
                stats["meilisearch"] = {"error": str(e)}
        
        return stats


# Convenience function
def index_file(file_path: str | Path) -> IndexResult:
    """
    Index a single file (convenience function).
    
    Args:
        file_path: Path to the file to index.
    
    Returns:
        IndexResult with indexing details.
    """
    indexer = DocumentIndexer()
    return indexer.index_file(file_path)
