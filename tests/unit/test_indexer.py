"""
Unit tests for DocumentIndexer module.

Tests the document indexing pipeline:
- Single file indexing
- Batch indexing
- Deduplication
- Error handling
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from indexation.indexer import (
    DocumentIndexer,
    IndexResult,
    BatchIndexResult,
    index_file,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_lancedb():
    """Create a mock LanceDB client."""
    client = MagicMock()
    client.add_document.return_value = "test_doc_id"
    client.get_document.return_value = None
    client.get_stats.return_value = {"document_count": 0, "table_name": "test"}
    client.delete.return_value = True
    return client


@pytest.fixture
def mock_meilisearch():
    """Create a mock Meilisearch client."""
    client = MagicMock()
    client.add_document.return_value = "test_doc_id"
    client.get_document.return_value = None
    client.is_healthy.return_value = True
    client.get_stats.return_value = {"document_count": 0, "index_name": "test"}
    client.delete.return_value = True
    return client


@pytest.fixture
def mock_text_extractor():
    """Create a mock TextExtractor."""
    from indexation.text_extractor import ExtractionResult
    
    extractor = MagicMock()
    extractor.extract.return_value = ExtractionResult(
        text="This is test content for indexing.",
        metadata={
            "word_count": 6,
            "language": "en",
            "file_type": "txt",
        },
        success=True,
    )
    extractor.get_supported_extensions.return_value = {".txt", ".pdf", ".md"}
    return extractor


@pytest.fixture
def indexer(mock_lancedb, mock_meilisearch, mock_text_extractor):
    """Create a DocumentIndexer with mocked dependencies."""
    return DocumentIndexer(
        lancedb_client=mock_lancedb,
        meilisearch_client=mock_meilisearch,
        text_extractor=mock_text_extractor,
    )


@pytest.fixture
def temp_txt_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello, this is a test document for indexing.\nIt has two lines.")
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_dir_with_files():
    """Create a temporary directory with test files."""
    import os
    tmpdir = tempfile.mkdtemp()
    
    # Create test files
    (Path(tmpdir) / "test1.txt").write_text("Test document one")
    (Path(tmpdir) / "test2.txt").write_text("Test document two")
    (Path(tmpdir) / "test3.md").write_text("# Test markdown")
    (Path(tmpdir) / "ignored.xyz").write_text("Should be ignored")
    
    # Create subdirectory
    subdir = Path(tmpdir) / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("Nested document")
    
    yield Path(tmpdir)
    
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir)


# =============================================================================
# IndexResult Tests
# =============================================================================

class TestIndexResult:
    """Tests for IndexResult dataclass."""
    
    def test_successful_result(self):
        """Test creating a successful index result."""
        result = IndexResult(
            path="/test/file.txt",
            doc_id="abc123",
            success=True,
            lancedb_indexed=True,
            meilisearch_indexed=True,
            word_count=100,
            language="en",
        )
        assert result.success
        assert result.lancedb_indexed
        assert result.meilisearch_indexed
        assert result.word_count == 100
    
    def test_failed_result(self):
        """Test creating a failed index result."""
        result = IndexResult(
            path="/test/file.txt",
            doc_id="abc123",
            success=False,
            error="Extraction failed",
        )
        assert not result.success
        assert result.error == "Extraction failed"
    
    def test_total_time(self):
        """Test total_time_ms property."""
        result = IndexResult(
            path="/test/file.txt",
            doc_id="abc123",
            extraction_time_ms=100.5,
            indexing_time_ms=50.3,
        )
        assert result.total_time_ms == pytest.approx(150.8)


class TestBatchIndexResult:
    """Tests for BatchIndexResult dataclass."""
    
    def test_empty_batch(self):
        """Test empty batch result."""
        result = BatchIndexResult()
        assert result.total == 0
        assert result.success_rate == 0.0
    
    def test_success_rate(self):
        """Test success rate calculation."""
        result = BatchIndexResult(
            total=10,
            successful=8,
            failed=2,
        )
        assert result.success_rate == 80.0
    
    def test_partial_success(self):
        """Test batch with mixed results."""
        result = BatchIndexResult(
            total=5,
            successful=3,
            failed=1,
            skipped=1,
        )
        assert result.total == 5
        assert result.success_rate == 60.0


# =============================================================================
# DocumentIndexer Tests
# =============================================================================

class TestDocumentIndexer:
    """Tests for DocumentIndexer class."""
    
    def test_init_with_mocks(self, indexer):
        """Test initialization with mocked clients."""
        assert indexer is not None
        assert indexer.lancedb is not None
        assert indexer.meilisearch is not None
    
    def test_init_skip_clients(self):
        """Test initialization with skipped clients."""
        indexer = DocumentIndexer(
            skip_lancedb=True,
            skip_meilisearch=True,
        )
        assert indexer.lancedb is None
        assert indexer.meilisearch is None
    
    def test_generate_id(self, indexer):
        """Test document ID generation."""
        id1 = indexer._generate_id("/path/to/file.txt")
        id2 = indexer._generate_id("/path/to/file.txt")
        id3 = indexer._generate_id("/path/to/other.txt")
        
        assert id1 == id2  # Same path = same ID
        assert id1 != id3  # Different path = different ID
        assert len(id1) == 64  # SHA256 hex length
    
    def test_get_category_document(self, indexer):
        """Test category detection for documents."""
        assert indexer._get_category(Path("/test/file.pdf")) == "document"
        assert indexer._get_category(Path("/test/file.docx")) == "document"
        assert indexer._get_category(Path("/test/file.odt")) == "document"
    
    def test_get_category_code(self, indexer):
        """Test category detection for code files."""
        assert indexer._get_category(Path("/test/file.py")) == "code"
        assert indexer._get_category(Path("/test/file.js")) == "code"
        assert indexer._get_category(Path("/test/file.ts")) == "code"
    
    def test_get_category_spreadsheet(self, indexer):
        """Test category detection for spreadsheets."""
        assert indexer._get_category(Path("/test/file.xlsx")) == "spreadsheet"
        assert indexer._get_category(Path("/test/file.csv")) == "spreadsheet"
    
    def test_get_category_other(self, indexer):
        """Test category detection for unknown types."""
        assert indexer._get_category(Path("/test/file.xyz")) == "other"


class TestIndexFile:
    """Tests for index_file method."""
    
    def test_index_success(self, indexer, temp_txt_file):
        """Test successful file indexing."""
        result = indexer.index_file(temp_txt_file)
        
        assert result.success
        assert result.lancedb_indexed
        assert result.meilisearch_indexed
        assert result.doc_id
        assert result.extraction_time_ms > 0
        assert result.indexing_time_ms > 0
    
    def test_index_nonexistent_file(self, indexer):
        """Test indexing nonexistent file."""
        result = indexer.index_file("/nonexistent/file.txt")
        
        assert not result.success
        assert "File not found" in result.error
    
    def test_index_directory(self, indexer, temp_dir_with_files):
        """Test indexing a directory (should fail)."""
        result = indexer.index_file(temp_dir_with_files)
        
        assert not result.success
        assert "Not a file" in result.error
    
    def test_index_extraction_failure(self, indexer, temp_txt_file):
        """Test handling of extraction failure."""
        from indexation.text_extractor import ExtractionResult
        
        indexer.text_extractor.extract.return_value = ExtractionResult(
            text="",
            success=False,
            error="Extraction failed",
        )
        
        result = indexer.index_file(temp_txt_file)
        
        assert not result.success
        assert "Extraction failed" in result.error
    
    def test_index_already_indexed(self, indexer, temp_txt_file, mock_meilisearch):
        """Test skipping already indexed file."""
        # Simulate document exists
        mock_meilisearch.get_document.return_value = {"id": "existing"}
        
        result = indexer.index_file(temp_txt_file)
        
        assert result.success
        assert "Already indexed" in result.error
    
    def test_index_force_reindex(self, indexer, temp_txt_file, mock_meilisearch):
        """Test force re-indexing."""
        # Simulate document exists
        mock_meilisearch.get_document.return_value = {"id": "existing"}
        
        result = indexer.index_file(temp_txt_file, force=True)
        
        assert result.success
        assert result.lancedb_indexed
        assert result.meilisearch_indexed
    
    def test_index_lancedb_failure(self, indexer, temp_txt_file, mock_lancedb):
        """Test handling of LanceDB failure."""
        from search.lancedb_client import LanceDBError
        
        mock_lancedb.add_document.side_effect = LanceDBError("Connection failed")
        
        result = indexer.index_file(temp_txt_file)
        
        assert not result.success
        assert not result.lancedb_indexed
        assert "LanceDB" in result.error
    
    def test_index_meilisearch_failure(self, indexer, temp_txt_file, mock_meilisearch):
        """Test handling of Meilisearch failure."""
        from search.meilisearch_client import MeilisearchError
        
        mock_meilisearch.add_document.side_effect = MeilisearchError("Connection failed")
        
        result = indexer.index_file(temp_txt_file)
        
        assert not result.success
        assert not result.meilisearch_indexed
        assert "Meilisearch" in result.error


class TestIndexFiles:
    """Tests for index_files batch method."""
    
    def test_batch_index_success(self, indexer, temp_dir_with_files):
        """Test batch indexing multiple files."""
        files = list(temp_dir_with_files.glob("*.txt"))
        
        result = indexer.index_files(files)
        
        assert result.total == len(files)
        assert result.successful == len(files)
        assert result.failed == 0
    
    def test_batch_with_failures(self, indexer, temp_dir_with_files):
        """Test batch indexing with some failures."""
        files = list(temp_dir_with_files.glob("*.txt"))
        files.append(Path("/nonexistent/file.txt"))
        
        result = indexer.index_files(files)
        
        assert result.total == len(files)
        assert result.failed == 1
    
    def test_batch_progress_callback(self, indexer, temp_dir_with_files):
        """Test progress callback during batch indexing."""
        files = list(temp_dir_with_files.glob("*.txt"))
        progress_calls = []
        
        def on_progress(current, total, result):
            progress_calls.append((current, total, result.success))
        
        indexer.index_files(files, on_progress=on_progress)
        
        assert len(progress_calls) == len(files)
        assert progress_calls[-1][0] == len(files)


class TestIndexDirectory:
    """Tests for index_directory method."""
    
    def test_index_directory(self, indexer, temp_dir_with_files):
        """Test indexing a directory."""
        result = indexer.index_directory(temp_dir_with_files, recursive=False)
        
        # Should find txt and md files, ignore xyz
        assert result.total == 3  # test1.txt, test2.txt, test3.md
    
    def test_index_directory_recursive(self, indexer, temp_dir_with_files):
        """Test recursive directory indexing."""
        result = indexer.index_directory(temp_dir_with_files, recursive=True)
        
        # Should find all txt and md files including nested
        assert result.total == 4  # test1.txt, test2.txt, test3.md, nested.txt
    
    def test_index_nonexistent_directory(self, indexer):
        """Test indexing nonexistent directory."""
        result = indexer.index_directory("/nonexistent/dir")
        
        assert result.total == 0
        assert len(result.results) == 1
        assert "Directory not found" in result.results[0].error


class TestDeleteDocument:
    """Tests for delete_document method."""
    
    def test_delete_success(self, indexer, temp_txt_file):
        """Test successful document deletion."""
        success, message = indexer.delete_document(temp_txt_file)
        
        assert success
        assert "Deleted" in message
    
    def test_delete_failure(self, indexer, temp_txt_file, mock_lancedb, mock_meilisearch):
        """Test deletion failure handling."""
        mock_lancedb.delete.side_effect = Exception("Delete failed")
        mock_meilisearch.delete.side_effect = Exception("Delete failed")
        
        success, message = indexer.delete_document(temp_txt_file)
        
        assert not success
        assert "LanceDB" in message or "Meilisearch" in message


class TestGetStats:
    """Tests for get_stats method."""
    
    def test_get_stats(self, indexer):
        """Test getting indexing statistics."""
        stats = indexer.get_stats()
        
        assert "lancedb" in stats
        assert "meilisearch" in stats
        assert stats["lancedb"]["document_count"] == 0
        assert stats["meilisearch"]["document_count"] == 0


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunction:
    """Tests for index_file convenience function."""
    
    @patch("indexation.indexer.DocumentIndexer")
    def test_index_file_function(self, mock_indexer_class):
        """Test index_file convenience function."""
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = IndexResult(
            path="/test/file.txt",
            doc_id="abc123",
            success=True,
        )
        mock_indexer_class.return_value = mock_indexer
        
        result = index_file("/test/file.txt")
        
        assert result.success
        mock_indexer.index_file.assert_called_once()


# =============================================================================
# Integration Tests (with real components, mocked search clients)
# =============================================================================

class TestIntegration:
    """Integration tests with real TextExtractor."""
    
    def test_real_extraction_mock_indexing(self, mock_lancedb, mock_meilisearch, temp_txt_file):
        """Test with real extraction but mocked indexing."""
        from indexation.text_extractor import TextExtractor
        
        indexer = DocumentIndexer(
            lancedb_client=mock_lancedb,
            meilisearch_client=mock_meilisearch,
            text_extractor=TextExtractor(),
        )
        
        result = indexer.index_file(temp_txt_file)
        
        assert result.success
        assert result.word_count > 0
        assert result.language is not None
    
    def test_skip_both_clients(self, temp_txt_file):
        """Test with both clients skipped (extraction only)."""
        from indexation.text_extractor import TextExtractor
        
        indexer = DocumentIndexer(
            skip_lancedb=True,
            skip_meilisearch=True,
            text_extractor=TextExtractor(),
        )
        
        result = indexer.index_file(temp_txt_file)
        
        assert result.success
        assert not result.lancedb_indexed
        assert not result.meilisearch_indexed
