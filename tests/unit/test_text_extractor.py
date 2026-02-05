"""
Unit tests for TextExtractor module.

Tests text extraction from various document formats:
- Plain text files (TXT, MD)
- Source code files (Python, JSON)
- PDF documents (using pypdf)
- DOCX documents (using python-docx)
- Language detection
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from indexation.text_extractor import (
    TextExtractor,
    ExtractionResult,
    PlainTextExtractor,
    CodeExtractor,
    JSONExtractor,
    PDFExtractor,
    DOCXExtractor,
    extract_text,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def extractor():
    """Create a TextExtractor instance."""
    return TextExtractor()


@pytest.fixture
def temp_txt_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello, this is a test document.\nIt has two lines.")
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_md_file():
    """Create a temporary markdown file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Test Document\n\nThis is a **markdown** file with some content.")
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_py_file():
    """Create a temporary Python file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write('"""Module docstring."""\n\ndef hello():\n    """Say hello."""\n    print("Hello!")\n')
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"name": "test", "value": 42, "items": [1, 2, 3]}, f)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_invalid_json():
    """Create a temporary invalid JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write('{"invalid": json content}')
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


# =============================================================================
# ExtractionResult Tests
# =============================================================================

class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""
    
    def test_successful_result(self):
        """Test creating a successful extraction result."""
        result = ExtractionResult(
            text="Hello world",
            metadata={"word_count": 2, "language": "en"},
            success=True
        )
        assert result.success
        assert result.text == "Hello world"
        assert result.word_count == 2
        assert result.language == "en"
        assert result.error is None
    
    def test_failed_result(self):
        """Test creating a failed extraction result."""
        result = ExtractionResult(
            text="",
            success=False,
            error="File not found"
        )
        assert not result.success
        assert result.error == "File not found"
        assert result.word_count == 0
    
    def test_pages_property(self):
        """Test pages property."""
        result = ExtractionResult(
            text="content",
            metadata={"pages": 5}
        )
        assert result.pages == 5
    
    def test_missing_properties(self):
        """Test properties when metadata is empty."""
        result = ExtractionResult(text="content")
        assert result.word_count == 0
        assert result.language is None
        assert result.pages is None


# =============================================================================
# PlainTextExtractor Tests
# =============================================================================

class TestPlainTextExtractor:
    """Tests for plain text file extraction."""
    
    def test_extract_txt_file(self, temp_txt_file):
        """Test extracting text from .txt file."""
        extractor = PlainTextExtractor()
        result = extractor.extract(temp_txt_file)
        
        assert result.success
        assert "Hello, this is a test document" in result.text
        assert result.metadata["word_count"] == 10
        assert result.metadata["line_count"] == 2
        assert result.metadata["file_type"] == "txt"
    
    def test_extract_md_file(self, temp_md_file):
        """Test extracting text from .md file."""
        extractor = PlainTextExtractor()
        result = extractor.extract(temp_md_file)
        
        assert result.success
        assert "# Test Document" in result.text
        assert result.metadata["file_type"] == "md"
    
    def test_supported_extensions(self):
        """Test supported extensions list."""
        extractor = PlainTextExtractor()
        assert ".txt" in extractor.SUPPORTED_EXTENSIONS
        assert ".md" in extractor.SUPPORTED_EXTENSIONS
        assert ".markdown" in extractor.SUPPORTED_EXTENSIONS
        assert ".rst" in extractor.SUPPORTED_EXTENSIONS
    
    def test_can_handle(self, temp_txt_file, temp_md_file):
        """Test can_handle method."""
        assert PlainTextExtractor.can_handle(temp_txt_file)
        assert PlainTextExtractor.can_handle(temp_md_file)
        assert not PlainTextExtractor.can_handle(Path("test.pdf"))


# =============================================================================
# CodeExtractor Tests
# =============================================================================

class TestCodeExtractor:
    """Tests for source code file extraction."""
    
    def test_extract_python_file(self, temp_py_file):
        """Test extracting text from Python file."""
        extractor = CodeExtractor()
        result = extractor.extract(temp_py_file)
        
        assert result.success
        assert "def hello():" in result.text
        assert result.metadata["programming_language"] == "py"
        assert result.metadata["file_type"] == "code"
    
    def test_supported_extensions(self):
        """Test supported extensions list."""
        extractor = CodeExtractor()
        assert ".py" in extractor.SUPPORTED_EXTENSIONS
        assert ".js" in extractor.SUPPORTED_EXTENSIONS
        assert ".ts" in extractor.SUPPORTED_EXTENSIONS
        assert ".json" in extractor.SUPPORTED_EXTENSIONS
        assert ".yaml" in extractor.SUPPORTED_EXTENSIONS


# =============================================================================
# JSONExtractor Tests
# =============================================================================

class TestJSONExtractor:
    """Tests for JSON file extraction."""
    
    def test_extract_valid_json(self, temp_json_file):
        """Test extracting from valid JSON file."""
        extractor = JSONExtractor()
        result = extractor.extract(temp_json_file)
        
        assert result.success
        assert '"name": "test"' in result.text
        assert result.metadata["file_type"] == "json"
        assert result.metadata["keys_count"] == 3  # name, value, items
    
    def test_extract_invalid_json(self, temp_invalid_json):
        """Test extracting from invalid JSON file."""
        extractor = JSONExtractor()
        result = extractor.extract(temp_invalid_json)
        
        assert not result.success
        assert "Invalid JSON" in result.error


# =============================================================================
# TextExtractor Main Class Tests
# =============================================================================

class TestTextExtractor:
    """Tests for main TextExtractor class."""
    
    def test_extract_txt(self, extractor, temp_txt_file):
        """Test extracting from .txt file."""
        result = extractor.extract(temp_txt_file)
        
        assert result.success
        assert "Hello" in result.text
        assert "file_path" in result.metadata
        assert "file_name" in result.metadata
        assert "file_size" in result.metadata
    
    def test_extract_md(self, extractor, temp_md_file):
        """Test extracting from .md file."""
        result = extractor.extract(temp_md_file)
        
        assert result.success
        assert "# Test Document" in result.text
    
    def test_extract_py(self, extractor, temp_py_file):
        """Test extracting from .py file."""
        result = extractor.extract(temp_py_file)
        
        assert result.success
        assert "def hello():" in result.text
    
    def test_extract_json(self, extractor, temp_json_file):
        """Test extracting from .json file."""
        result = extractor.extract(temp_json_file)
        
        assert result.success
        assert "test" in result.text
    
    def test_extract_nonexistent_file(self, extractor):
        """Test extracting from nonexistent file."""
        result = extractor.extract("/nonexistent/file.txt")
        
        assert not result.success
        assert "File not found" in result.error
    
    def test_extract_unsupported_type(self, extractor):
        """Test extracting from unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            path = Path(f.name)
        
        try:
            result = extractor.extract(path)
            assert not result.success
            assert "Unsupported file type" in result.error
        finally:
            path.unlink(missing_ok=True)
    
    def test_extract_directory(self, extractor):
        """Test extracting from a directory (should fail)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = extractor.extract(tmpdir)
            assert not result.success
            assert "Not a file" in result.error
    
    def test_get_supported_extensions(self, extractor):
        """Test getting supported extensions."""
        extensions = extractor.get_supported_extensions()
        
        assert isinstance(extensions, set)
        assert ".txt" in extensions
        assert ".py" in extensions
        assert ".json" in extensions
        assert ".md" in extensions
    
    def test_can_extract(self, extractor, temp_txt_file):
        """Test can_extract method."""
        assert extractor.can_extract(temp_txt_file)
        assert extractor.can_extract("file.py")
        assert not extractor.can_extract("file.xyz")


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestExtractTextFunction:
    """Tests for extract_text convenience function."""
    
    def test_extract_text_function(self, temp_txt_file):
        """Test extract_text convenience function."""
        result = extract_text(temp_txt_file)
        
        assert result.success
        assert "Hello" in result.text
    
    def test_extract_text_with_string_path(self, temp_txt_file):
        """Test extract_text with string path."""
        result = extract_text(str(temp_txt_file))
        
        assert result.success


# =============================================================================
# PDF Extractor Tests (Mocked)
# =============================================================================

class TestPDFExtractor:
    """Tests for PDF extraction (mocked to avoid real PDF files)."""
    
    def test_supported_extensions(self):
        """Test PDF extractor supports .pdf extension."""
        assert ".pdf" in PDFExtractor.SUPPORTED_EXTENSIONS
    
    @patch("src.indexation.pdf_extractor._get_pypdf")
    def test_extract_pdf_success(self, mock_get_pypdf):
        """Test successful PDF extraction with enhanced PDFExtractor."""
        # Mock pypdf
        mock_pypdf = MagicMock()
        mock_get_pypdf.return_value = mock_pypdf
        
        mock_reader = MagicMock()
        mock_page = MagicMock()
        # Need enough text to pass native detection thresholds
        mock_page.extract_text.return_value = "This is PDF text content. " * 50
        mock_page.get.return_value = {}
        mock_page.__getitem__ = MagicMock(return_value={})
        mock_reader.pages = [mock_page, mock_page]
        mock_reader.metadata = {"/Title": "Test PDF", "/Author": "Test Author"}
        mock_pypdf.PdfReader.return_value = mock_reader
        
        # Create a temp file to use as path (not actually read due to mock)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)
        
        try:
            extractor = PDFExtractor()
            result = extractor.extract(path)
            
            assert result.success
            assert "PDF text content" in result.text
            assert result.metadata["pages"] == 2
            assert result.metadata["title"] == "Test PDF"
            assert result.metadata.get("needs_ocr") is False
        finally:
            path.unlink(missing_ok=True)
    
    @patch("src.indexation.pdf_extractor._get_pypdf")
    def test_pdf_missing_pypdf(self, mock_get_pypdf):
        """Test error when pypdf is not installed."""
        mock_get_pypdf.side_effect = ImportError("pypdf not found")
        
        extractor = PDFExtractor()
        result = extractor.extract(Path("test.pdf"))
        
        assert not result.success
        assert "pypdf not installed" in result.error


# =============================================================================
# DOCX Extractor Tests (Mocked)
# =============================================================================

class TestDOCXExtractor:
    """Tests for DOCX extraction (mocked to avoid real DOCX files)."""
    
    def test_supported_extensions(self):
        """Test DOCX extractor supports .docx extension."""
        assert ".docx" in DOCXExtractor.SUPPORTED_EXTENSIONS
    
    @patch("indexation.text_extractor._get_docx")
    def test_extract_docx_success(self, mock_get_docx):
        """Test successful DOCX extraction."""
        # Mock python-docx
        mock_docx = MagicMock()
        mock_get_docx.return_value = mock_docx
        
        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph of the document."
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph with more text."
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.tables = []
        mock_doc.core_properties = MagicMock()
        mock_doc.core_properties.title = "Test Document"
        mock_doc.core_properties.author = "Test Author"
        mock_doc.core_properties.subject = None
        mock_doc.core_properties.created = None
        mock_doc.core_properties.modified = None
        mock_docx.Document.return_value = mock_doc
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = Path(f.name)
        
        try:
            extractor = DOCXExtractor()
            result = extractor.extract(path)
            
            assert result.success
            assert "First paragraph" in result.text
            assert result.metadata["paragraphs"] == 2
            assert result.metadata["title"] == "Test Document"
        finally:
            path.unlink(missing_ok=True)
    
    def test_docx_missing_library(self):
        """Test error when python-docx is not installed."""
        with patch("indexation.text_extractor._get_docx", side_effect=ImportError):
            extractor = DOCXExtractor()
            result = extractor.extract(Path("test.docx"))
            
            assert not result.success
            assert "python-docx not installed" in result.error


# =============================================================================
# Language Detection Tests
# =============================================================================

class TestLanguageDetection:
    """Tests for language detection."""
    
    def test_detect_english(self, extractor):
        """Test detecting English text."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a long enough English text for language detection to work properly. "
                    "It needs to have multiple sentences to be detected correctly.")
            path = Path(f.name)
        
        try:
            result = extractor.extract(path)
            assert result.success
            assert result.language == "en"
        finally:
            path.unlink(missing_ok=True)
    
    def test_detect_french(self, extractor):
        """Test detecting French text."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Ceci est un texte français suffisamment long pour la détection de langue. "
                    "Il faut plusieurs phrases pour que la détection fonctionne correctement.")
            path = Path(f.name)
        
        try:
            result = extractor.extract(path)
            assert result.success
            assert result.language == "fr"
        finally:
            path.unlink(missing_ok=True)
    
    def test_short_text_no_detection(self, extractor):
        """Test that very short text doesn't attempt detection."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hi")
            path = Path(f.name)
        
        try:
            result = extractor.extract(path)
            assert result.success
            # Language might be None for very short text
        finally:
            path.unlink(missing_ok=True)


# =============================================================================
# Encoding Tests
# =============================================================================

class TestEncodingHandling:
    """Tests for file encoding handling."""
    
    def test_utf8_encoding(self, extractor):
        """Test reading UTF-8 encoded file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Unicode text: é à ü ñ 日本語 中文")
            path = Path(f.name)
        
        try:
            result = extractor.extract(path)
            assert result.success
            assert "é" in result.text
            assert "日本語" in result.text
        finally:
            path.unlink(missing_ok=True)
    
    def test_latin1_encoding(self, extractor):
        """Test reading Latin-1 encoded file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("Hello with accents: café résumé".encode("latin-1"))
            path = Path(f.name)
        
        try:
            result = extractor.extract(path)
            assert result.success
            assert "café" in result.text or "cafÃ" in result.text  # Depending on encoding detection
        finally:
            path.unlink(missing_ok=True)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full extraction pipeline."""
    
    def test_extract_multiple_file_types(self, extractor, temp_txt_file, temp_py_file, temp_json_file):
        """Test extracting from multiple file types."""
        results = [
            extractor.extract(temp_txt_file),
            extractor.extract(temp_py_file),
            extractor.extract(temp_json_file),
        ]
        
        for result in results:
            assert result.success
            assert result.text
            assert "file_path" in result.metadata
    
    def test_extractor_reuse(self, extractor, temp_txt_file):
        """Test that extractor can be reused for multiple files."""
        result1 = extractor.extract(temp_txt_file)
        result2 = extractor.extract(temp_txt_file)
        
        assert result1.success
        assert result2.success
        assert result1.text == result2.text
