"""
Tests for FilesystemScanner.

Tests document discovery, exclusion patterns, and change detection.
"""

import pytest
import tempfile
import shutil
import time
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from indexation.scanner import FilesystemScanner, FileInfo, ScanResult


class TestFileInfo:
    """Test FileInfo dataclass."""
    
    def test_file_info_creation(self):
        """Test basic FileInfo creation."""
        info = FileInfo(
            path="/test/file.pdf",
            size=1024,
            mtime=1234567890.0
        )
        assert info.path == "/test/file.pdf"
        assert info.size == 1024
        assert info.extension == ".pdf"
    
    def test_file_info_extension_extraction(self):
        """Test extension is extracted from path."""
        info = FileInfo(path="/test/doc.DOCX", size=100, mtime=0)
        assert info.extension == ".docx"  # lowercase
    
    def test_file_info_to_dict(self):
        """Test serialization to dict."""
        info = FileInfo(
            path="/test/file.pdf",
            size=1024,
            mtime=1234567890.0,
            sha256="abc123"
        )
        d = info.to_dict()
        assert d["path"] == "/test/file.pdf"
        assert d["sha256"] == "abc123"
    
    def test_file_info_from_dict(self):
        """Test deserialization from dict."""
        d = {
            "path": "/test/file.pdf",
            "size": 1024,
            "mtime": 1234567890.0,
            "sha256": "abc123",
            "extension": ".pdf"
        }
        info = FileInfo.from_dict(d)
        assert info.path == "/test/file.pdf"
        assert info.sha256 == "abc123"


class TestScanResult:
    """Test ScanResult dataclass."""
    
    def test_scan_result_empty(self):
        """Test empty scan result."""
        result = ScanResult()
        assert not result.has_changes
        assert result.total_scanned == 0
    
    def test_scan_result_with_new_files(self):
        """Test scan result with new files."""
        info = FileInfo(path="/test/new.pdf", size=100, mtime=0)
        result = ScanResult(new_files=[info])
        assert result.has_changes
    
    def test_scan_result_with_deleted(self):
        """Test scan result with deleted paths."""
        result = ScanResult(deleted_paths=["/old/file.pdf"])
        assert result.has_changes


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.mkdtemp(prefix="aitao_scan_test_")
    
    # Create test structure
    # temp_dir/
    #   docs/
    #     file1.pdf
    #     file2.docx
    #     subdir/
    #       file3.txt
    #   images/
    #     photo.jpg
    #   hidden/
    #     .hidden_file
    #   __pycache__/
    #     cache.pyc
    #   .git/
    #     config
    
    docs_dir = Path(temp_dir) / "docs"
    docs_dir.mkdir()
    (docs_dir / "file1.pdf").write_text("PDF content")
    (docs_dir / "file2.docx").write_text("DOCX content")
    
    subdir = docs_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("TXT content")
    
    images_dir = Path(temp_dir) / "images"
    images_dir.mkdir()
    (images_dir / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0")  # JPEG magic
    
    hidden_dir = Path(temp_dir) / "hidden"
    hidden_dir.mkdir()
    (hidden_dir / ".hidden_file").write_text("hidden")
    
    pycache_dir = Path(temp_dir) / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "cache.pyc").write_bytes(b"bytecode")
    
    git_dir = Path(temp_dir) / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_test_dir, tmp_path):
    """Create a mock config file for testing."""
    config_content = f"""
[paths]
storage_root = "{tmp_path}"

[indexing]
enabled = true
include_paths = ["{temp_test_dir}"]
exclude_dirs = ["__pycache__", ".git", "node_modules"]
exclude_files = [".DS_Store"]
exclude_extensions = [".log", ".tmp"]
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    return str(config_file)


class TestFilesystemScanner:
    """Test FilesystemScanner class."""
    
    def test_scanner_initialization(self, mock_config, temp_test_dir):
        """Test scanner initializes correctly."""
        scanner = FilesystemScanner(config_path=mock_config)
        
        assert len(scanner.include_paths) == 1
        assert str(scanner.include_paths[0]) == temp_test_dir
        assert "__pycache__" in scanner.exclude_dirs
    
    def test_scan_finds_supported_files(self, mock_config, temp_test_dir):
        """Test scan discovers supported file types."""
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan()
        
        # Should find: file1.pdf, file2.docx, file3.txt, photo.jpg
        assert result.total_scanned == 4
        assert len(result.new_files) == 4
        
        paths = [f.path for f in result.new_files]
        assert any("file1.pdf" in p for p in paths)
        assert any("photo.jpg" in p for p in paths)
    
    def test_scan_excludes_hidden_dirs(self, mock_config, temp_test_dir):
        """Test that hidden directories are skipped."""
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan()
        
        paths = [f.path for f in result.new_files]
        # .git and hidden dirs should be skipped
        assert not any(".git" in p for p in paths)
        assert not any(".hidden" in p for p in paths)
    
    def test_scan_excludes_pycache(self, mock_config, temp_test_dir):
        """Test that __pycache__ is excluded."""
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan()
        
        paths = [f.path for f in result.new_files]
        assert not any("__pycache__" in p for p in paths)
        assert not any(".pyc" in p for p in paths)
    
    def test_scan_detects_new_files(self, mock_config, temp_test_dir):
        """Test new file detection on second scan."""
        scanner = FilesystemScanner(config_path=mock_config)
        
        # First scan
        result1 = scanner.scan()
        assert len(result1.new_files) == 4
        
        # Add a new file
        new_file = Path(temp_test_dir) / "docs" / "new_doc.pdf"
        new_file.write_text("New PDF")
        
        # Second scan
        result2 = scanner.scan()
        assert len(result2.new_files) == 1
        assert "new_doc.pdf" in result2.new_files[0].path
    
    def test_scan_detects_modified_files(self, mock_config, temp_test_dir):
        """Test modified file detection."""
        scanner = FilesystemScanner(config_path=mock_config)
        
        # First scan
        result1 = scanner.scan()
        initial_count = len(result1.new_files)
        
        # Wait a bit and modify a file
        time.sleep(0.1)
        modified_file = Path(temp_test_dir) / "docs" / "file1.pdf"
        modified_file.write_text("Modified PDF content")
        
        # Second scan
        result2 = scanner.scan()
        assert len(result2.modified_files) == 1
        assert "file1.pdf" in result2.modified_files[0].path
    
    def test_scan_detects_deleted_files(self, mock_config, temp_test_dir):
        """Test deleted file detection."""
        scanner = FilesystemScanner(config_path=mock_config)
        
        # First scan
        result1 = scanner.scan()
        
        # Delete a file
        deleted_file = Path(temp_test_dir) / "docs" / "file2.docx"
        deleted_file.unlink()
        
        # Second scan
        result2 = scanner.scan()
        assert len(result2.deleted_paths) == 1
        assert "file2.docx" in result2.deleted_paths[0]
    
    def test_scan_computes_hash(self, mock_config, temp_test_dir):
        """Test SHA256 hash computation."""
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan(compute_hashes=True)
        
        for file_info in result.new_files:
            assert file_info.sha256 is not None
            assert len(file_info.sha256) == 64  # SHA256 hex length
    
    def test_scan_without_hash(self, mock_config, temp_test_dir):
        """Test scanning without hash computation."""
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan(compute_hashes=False)
        
        for file_info in result.new_files:
            assert file_info.sha256 is None
    
    def test_scan_specific_paths(self, mock_config, temp_test_dir):
        """Test scanning specific paths."""
        scanner = FilesystemScanner(config_path=mock_config)
        
        docs_path = str(Path(temp_test_dir) / "docs")
        result = scanner.scan(paths=[docs_path])
        
        # Should only find files in docs/ (3 files)
        assert result.total_scanned == 3
        paths = [f.path for f in result.new_files]
        assert not any("photo.jpg" in p for p in paths)
    
    def test_get_stats(self, mock_config, temp_test_dir):
        """Test get_stats method."""
        scanner = FilesystemScanner(config_path=mock_config)
        scanner.scan()
        
        stats = scanner.get_stats()
        assert "include_paths" in stats
        assert stats["tracked_files"] == 4
    
    def test_clear_state(self, mock_config, temp_test_dir):
        """Test clearing scanner state."""
        scanner = FilesystemScanner(config_path=mock_config)
        scanner.scan()
        
        assert scanner.get_stats()["tracked_files"] == 4
        
        scanner.clear_state()
        assert scanner.get_stats()["tracked_files"] == 0
    
    def test_state_persistence(self, mock_config, temp_test_dir, tmp_path):
        """Test that state is persisted between scanner instances."""
        # First scanner instance
        scanner1 = FilesystemScanner(config_path=mock_config)
        result1 = scanner1.scan()
        assert len(result1.new_files) == 4
        
        # New scanner instance (same config)
        scanner2 = FilesystemScanner(config_path=mock_config)
        result2 = scanner2.scan()
        
        # Should detect no new files (state was loaded)
        assert len(result2.new_files) == 0
        assert len(result2.modified_files) == 0


class TestFilesystemScannerExtensions:
    """Test extension filtering."""
    
    def test_unsupported_extension_skipped(self, mock_config, temp_test_dir):
        """Test that unsupported extensions are skipped."""
        # Create a .xyz file (unsupported)
        xyz_file = Path(temp_test_dir) / "docs" / "test.xyz"
        xyz_file.write_text("xyz content")
        
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan()
        
        paths = [f.path for f in result.new_files]
        assert not any(".xyz" in p for p in paths)
    
    def test_excluded_extension_skipped(self, mock_config, temp_test_dir):
        """Test that excluded extensions are skipped."""
        # Create a .log file (excluded in config)
        log_file = Path(temp_test_dir) / "docs" / "test.log"
        log_file.write_text("log content")
        
        scanner = FilesystemScanner(config_path=mock_config)
        result = scanner.scan()
        
        paths = [f.path for f in result.new_files]
        assert not any(".log" in p for p in paths)
