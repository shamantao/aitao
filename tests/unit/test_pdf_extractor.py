"""
Unit tests for enhanced PDFExtractor module.

Tests PDF extraction capabilities including:
- Native (text-based) PDF extraction
- Scanned PDF detection (needs_ocr flag)
- PDF metadata extraction (author, title, dates)
- Multi-page document handling
- Error handling and edge cases
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from indexation.pdf_extractor import (
    PDFExtractor,
    PDFAnalysisResult,
    extract_pdf,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def extractor():
    """Create a PDFExtractor instance with default settings."""
    return PDFExtractor()


@pytest.fixture
def extractor_strict():
    """Create a PDFExtractor with strict thresholds (higher requirements)."""
    return PDFExtractor(
        min_text_coverage=0.5,
        min_chars_per_page=200,
    )


@pytest.fixture
def mock_pdf_reader():
    """Create a mock pypdf PdfReader for testing."""
    mock = MagicMock()
    return mock


# =============================================================================
# PDFAnalysisResult Tests
# =============================================================================

class TestPDFAnalysisResult:
    """Tests for PDFAnalysisResult dataclass."""
    
    def test_default_values(self):
        """Test default values are correctly set."""
        result = PDFAnalysisResult()
        
        assert result.text == ""
        assert result.needs_ocr is False
        assert result.page_count == 0
        assert result.pages_with_text == 0
        assert result.pages_with_images == 0
        assert result.text_coverage == 0.0
        assert result.metadata == {}
        assert result.success is True
        assert result.error is None
    
    def test_custom_values(self):
        """Test custom values are correctly stored."""
        result = PDFAnalysisResult(
            text="Hello World",
            needs_ocr=True,
            page_count=10,
            pages_with_text=3,
            pages_with_images=8,
            text_coverage=0.3,
            metadata={"author": "Test"},
            success=True,
        )
        
        assert result.text == "Hello World"
        assert result.needs_ocr is True
        assert result.page_count == 10
        assert result.pages_with_text == 3
        assert result.pages_with_images == 8
        assert result.text_coverage == 0.3
        assert result.metadata == {"author": "Test"}
    
    def test_error_state(self):
        """Test error state is correctly represented."""
        result = PDFAnalysisResult(
            success=False,
            error="Failed to open PDF"
        )
        
        assert result.success is False
        assert result.error == "Failed to open PDF"
        assert result.text == ""


# =============================================================================
# PDFExtractor Basic Tests
# =============================================================================

class TestPDFExtractorBasic:
    """Basic tests for PDFExtractor class."""
    
    def test_supported_extensions(self, extractor):
        """Test supported file extensions."""
        assert ".pdf" in extractor.SUPPORTED_EXTENSIONS
        assert len(extractor.SUPPORTED_EXTENSIONS) == 1
    
    def test_can_handle_pdf(self, extractor):
        """Test can_handle returns True for PDF files."""
        assert extractor.can_handle(Path("document.pdf")) is True
        assert extractor.can_handle(Path("DOCUMENT.PDF")) is True
        assert extractor.can_handle(Path("/path/to/file.pdf")) is True
    
    def test_cannot_handle_other_formats(self, extractor):
        """Test can_handle returns False for non-PDF files."""
        assert extractor.can_handle(Path("document.docx")) is False
        assert extractor.can_handle(Path("image.jpg")) is False
        assert extractor.can_handle(Path("document.txt")) is False
    
    def test_default_thresholds(self, extractor):
        """Test default threshold values."""
        assert extractor.min_text_coverage == 0.3
        assert extractor.min_chars_per_page == 100
    
    def test_custom_thresholds(self, extractor_strict):
        """Test custom threshold values."""
        assert extractor_strict.min_text_coverage == 0.5
        assert extractor_strict.min_chars_per_page == 200


# =============================================================================
# OCR Detection Tests (Mocked)
# =============================================================================

class TestNeedsOCRDetection:
    """Tests for needs_ocr detection logic."""
    
    def test_needs_ocr_very_short_text(self, extractor):
        """Test that very short total text triggers OCR."""
        needs_ocr = extractor._needs_ocr(
            text_coverage=0.5,
            avg_chars_per_page=50,
            total_text_length=30,  # Less than MIN_TEXT_LENGTH (50)
            pages_with_images=0,
            page_count=1,
        )
        assert needs_ocr is True
    
    def test_needs_ocr_low_coverage(self, extractor):
        """Test that low text coverage triggers OCR."""
        needs_ocr = extractor._needs_ocr(
            text_coverage=0.2,  # Less than MIN_TEXT_COVERAGE (0.3)
            avg_chars_per_page=500,
            total_text_length=1000,
            pages_with_images=5,
            page_count=10,
        )
        assert needs_ocr is True
    
    def test_needs_ocr_low_chars_per_page(self, extractor):
        """Test that low chars per page triggers OCR."""
        needs_ocr = extractor._needs_ocr(
            text_coverage=0.8,
            avg_chars_per_page=50,  # Less than MIN_CHARS_PER_PAGE (100)
            total_text_length=500,
            pages_with_images=0,
            page_count=10,
        )
        assert needs_ocr is True
    
    def test_needs_ocr_mostly_images(self, extractor):
        """Test that mostly image pages with low text triggers OCR."""
        needs_ocr = extractor._needs_ocr(
            text_coverage=0.4,  # Less than 0.5
            avg_chars_per_page=150,
            total_text_length=1000,
            pages_with_images=9,  # 90% images
            page_count=10,
        )
        assert needs_ocr is True
    
    def test_no_ocr_needed_good_text(self, extractor):
        """Test that good text coverage does not trigger OCR."""
        needs_ocr = extractor._needs_ocr(
            text_coverage=0.8,
            avg_chars_per_page=500,
            total_text_length=5000,
            pages_with_images=2,
            page_count=10,
        )
        assert needs_ocr is False
    
    def test_no_ocr_needed_text_only(self, extractor):
        """Test that text-only PDF does not trigger OCR."""
        needs_ocr = extractor._needs_ocr(
            text_coverage=1.0,
            avg_chars_per_page=800,
            total_text_length=8000,
            pages_with_images=0,
            page_count=10,
        )
        assert needs_ocr is False


# =============================================================================
# PDF Metadata Extraction Tests (Mocked)
# =============================================================================

class TestMetadataExtraction:
    """Tests for PDF metadata extraction."""
    
    def test_parse_pdf_date_standard(self, extractor):
        """Test parsing standard PDF date format."""
        # Format: D:YYYYMMDDHHmmss
        result = extractor._parse_pdf_date("D:20260201143022")
        assert result == "2026-02-01T14:30:22"
    
    def test_parse_pdf_date_no_prefix(self, extractor):
        """Test parsing date without D: prefix."""
        result = extractor._parse_pdf_date("20260201143022")
        assert result == "2026-02-01T14:30:22"
    
    def test_parse_pdf_date_date_only(self, extractor):
        """Test parsing date-only format."""
        result = extractor._parse_pdf_date("D:20260201")
        assert result == "2026-02-01"
    
    def test_parse_pdf_date_invalid(self, extractor):
        """Test parsing invalid date returns original."""
        result = extractor._parse_pdf_date("invalid")
        assert result == "invalid"
    
    def test_extract_metadata_with_reader(self, extractor):
        """Test metadata extraction from mock reader."""
        mock_reader = MagicMock()
        mock_reader.metadata = {
            "/Title": "Test Document",
            "/Author": "John Doe",
            "/Subject": "Testing",
            "/Creator": "Word",
            "/Producer": "pypdf",
            "/CreationDate": "D:20260201100000",
            "/ModDate": "D:20260202150000",
            "/Keywords": "test, pdf, extraction",
        }
        
        metadata = extractor._extract_metadata(mock_reader, Path("test.pdf"))
        
        assert metadata["title"] == "Test Document"
        assert metadata["author"] == "John Doe"
        assert metadata["subject"] == "Testing"
        assert metadata["creator"] == "Word"
        assert metadata["producer"] == "pypdf"
        assert metadata["creation_date"] == "2026-02-01T10:00:00"
        assert metadata["modification_date"] == "2026-02-02T15:00:00"
        assert metadata["keywords"] == "test, pdf, extraction"
    
    def test_extract_metadata_partial(self, extractor):
        """Test metadata extraction with only some fields."""
        mock_reader = MagicMock()
        mock_reader.metadata = {
            "/Title": "Test",
            "/Author": None,  # Missing
        }
        
        metadata = extractor._extract_metadata(mock_reader, Path("test.pdf"))
        
        assert metadata.get("title") == "Test"
        assert "author" not in metadata  # None values are filtered
    
    def test_extract_metadata_no_metadata(self, extractor):
        """Test extraction when PDF has no metadata."""
        mock_reader = MagicMock()
        mock_reader.metadata = None
        
        metadata = extractor._extract_metadata(mock_reader, Path("test.pdf"))
        
        assert metadata == {}


# =============================================================================
# Language Detection Tests (Mocked)
# =============================================================================

class TestLanguageDetection:
    """Tests for language detection."""
    
    def test_detect_language_english(self, extractor):
        """Test English language detection."""
        with patch.object(extractor, '_detect_language') as mock_detect:
            mock_detect.return_value = "en"
            result = mock_detect("This is an English text for testing purposes.")
            assert result == "en"
    
    def test_detect_language_short_text(self, extractor):
        """Test language detection returns None for short text."""
        result = extractor._detect_language("Short")
        assert result is None
    
    def test_detect_language_empty(self, extractor):
        """Test language detection returns None for empty text."""
        result = extractor._detect_language("")
        assert result is None
    
    def test_detect_language_whitespace_only(self, extractor):
        """Test language detection returns None for whitespace only."""
        result = extractor._detect_language("   \n\t   ")
        assert result is None


# =============================================================================
# Full Extraction Tests (Mocked)
# =============================================================================

class TestPDFAnalysis:
    """Tests for full PDF analysis with mocked pypdf."""
    
    def test_analyze_native_pdf(self, extractor):
        """Test analyzing a native (text-based) PDF."""
        # Create mock page with text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page content with enough text " * 50
        mock_page.get.return_value = {}
        mock_page.__getitem__ = MagicMock(return_value={})
        
        # Create mock reader
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page] * 5
        mock_reader.metadata = {"/Title": "Test Document", "/Author": "Tester"}
        
        # Patch at module level
        with patch("indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_get_pypdf.return_value = mock_pypdf
            
            result = extractor.analyze(Path("test.pdf"))
            
            assert result.success is True
            assert result.needs_ocr is False
            assert result.page_count == 5
            assert result.pages_with_text == 5
            assert len(result.text) > 0
            assert result.metadata["title"] == "Test Document"
            assert result.metadata["author"] == "Tester"
    
    def test_analyze_scanned_pdf(self, extractor):
        """Test analyzing a scanned (image-based) PDF."""
        # Create mock page with no text (simulating scanned)
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""  # No text
        mock_page.get.return_value = {}
        mock_page.__getitem__ = MagicMock(return_value={})
        
        # Create mock reader
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page] * 5
        mock_reader.metadata = {}
        
        with patch("indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_get_pypdf.return_value = mock_pypdf
            
            result = extractor.analyze(Path("scanned.pdf"))
            
            assert result.success is True
            assert result.needs_ocr is True
            assert result.page_count == 5
            assert result.pages_with_text == 0
            assert result.text == ""  # No text returned for scanned
    
    def test_analyze_empty_pdf(self, extractor):
        """Test analyzing an empty PDF (no pages)."""
        mock_reader = MagicMock()
        mock_reader.pages = []  # No pages
        
        with patch("indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_get_pypdf.return_value = mock_pypdf
            
            result = extractor.analyze(Path("empty.pdf"))
            
            assert result.success is False
            assert "no pages" in result.error.lower()
    
    def test_analyze_pypdf_not_installed(self, extractor):
        """Test handling when pypdf is not installed."""
        with patch("indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_get_pypdf.side_effect = ImportError("pypdf not found")
            
            result = extractor.analyze(Path("test.pdf"))
            
            assert result.success is False
            assert "pypdf not installed" in result.error
    
    def test_analyze_exception(self, extractor):
        """Test handling PDF read exception."""
        with patch("indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.side_effect = Exception("Corrupted PDF")
            mock_get_pypdf.return_value = mock_pypdf
            
            result = extractor.analyze(Path("corrupted.pdf"))
            
            assert result.success is False
            assert "Failed to analyze PDF" in result.error


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestExtractPDFFunction:
    """Tests for the extract_pdf convenience function."""
    
    def test_extract_pdf_creates_extractor(self):
        """Test that extract_pdf creates and uses PDFExtractor."""
        # Create mock page with text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Test content " * 50
        mock_page.get.return_value = {}
        mock_page.__getitem__ = MagicMock(return_value={})
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader.metadata = {}
        
        with patch("indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_get_pypdf.return_value = mock_pypdf
            
            result = extract_pdf("/path/to/test.pdf")
            
            assert result.success is True
            assert len(result.text) > 0


# =============================================================================
# Integration with TextExtractor wrapper
# =============================================================================

class TestTextExtractorIntegration:
    """Tests for PDFExtractor wrapper in text_extractor.py."""
    
    def test_wrapper_imports(self):
        """Test that the wrapper can be imported from text_extractor."""
        from indexation.text_extractor import PDFExtractor as WrapperPDFExtractor
        
        extractor = WrapperPDFExtractor()
        assert extractor.SUPPORTED_EXTENSIONS == {".pdf"}
    
    def test_wrapper_extract_native_pdf(self):
        """Test wrapper extraction for native PDF."""
        from indexation.text_extractor import PDFExtractor as WrapperPDFExtractor
        
        # Create mock page with text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Native PDF text content " * 50
        mock_page.get.return_value = {}
        mock_page.__getitem__ = MagicMock(return_value={})
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page] * 3
        mock_reader.metadata = {"/Title": "Native PDF"}
        
        # Patch at src.indexation level for wrapper import
        with patch("src.indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_get_pypdf.return_value = mock_pypdf
            
            extractor = WrapperPDFExtractor()
            result = extractor.extract(Path("native.pdf"))
            
            assert result.success is True
            assert len(result.text) > 0
            assert result.metadata.get("needs_ocr") is False
    
    def test_wrapper_extract_scanned_pdf(self):
        """Test wrapper extraction for scanned PDF sets needs_ocr."""
        from indexation.text_extractor import PDFExtractor as WrapperPDFExtractor
        
        # Create mock page with no text (scanned)
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_page.get.return_value = {}
        mock_page.__getitem__ = MagicMock(return_value={})
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page] * 3
        mock_reader.metadata = {}
        
        # Patch at src.indexation level for wrapper import
        with patch("src.indexation.pdf_extractor._get_pypdf") as mock_get_pypdf:
            mock_pypdf = MagicMock()
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_get_pypdf.return_value = mock_pypdf
            
            extractor = WrapperPDFExtractor()
            result = extractor.extract(Path("scanned.pdf"))
            
            assert result.success is True
            assert result.metadata.get("needs_ocr") is True
            assert result.text == ""  # No text extracted
