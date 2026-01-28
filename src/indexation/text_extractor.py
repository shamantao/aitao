"""
TextExtractor - Extract text content from various document formats.

This module provides text extraction capabilities for document indexing.
Supports PDF, DOCX, TXT, MD, JSON, TOML, and source code files.

Responsibilities:
- Extract raw text from documents without OCR
- Detect document language
- Calculate metadata (word count, page count, etc.)
- Handle encoding detection for text files
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, Type
import json
import logging

# Lazy imports for optional dependencies
_pypdf = None
_docx = None
_langdetect = None


def _get_pypdf():
    """Lazy load pypdf."""
    global _pypdf
    if _pypdf is None:
        import pypdf
        _pypdf = pypdf
    return _pypdf


def _get_docx():
    """Lazy load python-docx."""
    global _docx
    if _docx is None:
        import docx
        _docx = docx
    return _docx


def _get_langdetect():
    """Lazy load langdetect."""
    global _langdetect
    if _langdetect is None:
        import langdetect
        _langdetect = langdetect
    return _langdetect


logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of text extraction from a document."""
    
    text: str
    """Extracted text content."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Document metadata (pages, word_count, language, etc.)."""
    
    success: bool = True
    """Whether extraction was successful."""
    
    error: Optional[str] = None
    """Error message if extraction failed."""
    
    @property
    def word_count(self) -> int:
        """Return word count from metadata."""
        return self.metadata.get("word_count", 0)
    
    @property
    def language(self) -> Optional[str]:
        """Return detected language from metadata."""
        return self.metadata.get("language")
    
    @property
    def pages(self) -> Optional[int]:
        """Return page count from metadata."""
        return self.metadata.get("pages")


class BaseExtractor(ABC):
    """Abstract base class for text extractors."""
    
    # File extensions this extractor handles
    SUPPORTED_EXTENSIONS: set = set()
    
    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from a file.
        
        Args:
            file_path: Path to the file to extract text from.
            
        Returns:
            ExtractionResult with text and metadata.
        """
        pass
    
    @classmethod
    def can_handle(cls, file_path: Path) -> bool:
        """Check if this extractor can handle the given file."""
        return file_path.suffix.lower() in cls.SUPPORTED_EXTENSIONS


class PlainTextExtractor(BaseExtractor):
    """Extractor for plain text files (TXT, MD, etc.)."""
    
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".tex"}
    
    # Common encodings to try
    ENCODINGS = ["utf-8", "utf-16", "latin-1", "cp1252", "iso-8859-1"]
    
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text from plain text file."""
        text = None
        encoding_used = None
        
        # Try different encodings
        for encoding in self.ENCODINGS:
            try:
                text = file_path.read_text(encoding=encoding)
                encoding_used = encoding
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if text is None:
            return ExtractionResult(
                text="",
                success=False,
                error=f"Could not decode file with any encoding: {self.ENCODINGS}"
            )
        
        # Calculate metadata
        word_count = len(text.split())
        line_count = text.count("\n") + 1
        
        # Detect language
        language = self._detect_language(text)
        
        return ExtractionResult(
            text=text,
            metadata={
                "word_count": word_count,
                "line_count": line_count,
                "language": language,
                "encoding": encoding_used,
                "file_type": file_path.suffix.lower().lstrip("."),
            }
        )
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        if not text or len(text.strip()) < 20:
            return None
        
        try:
            langdetect = _get_langdetect()
            # Use first 5000 chars for detection
            sample = text[:5000]
            return langdetect.detect(sample)
        except Exception:
            return None


class CodeExtractor(BaseExtractor):
    """Extractor for source code files."""
    
    SUPPORTED_EXTENSIONS = {
        # Python
        ".py", ".pyi", ".pyx",
        # JavaScript/TypeScript
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        # Web
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        # Data formats
        ".json", ".yaml", ".yml", ".toml", ".xml",
        # Shell
        ".sh", ".bash", ".zsh", ".fish",
        # Other
        ".sql", ".r", ".rb", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
        ".java", ".kt", ".swift", ".m", ".mm",
    }
    
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text from source code file."""
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="latin-1")
            except Exception as e:
                return ExtractionResult(
                    text="",
                    success=False,
                    error=f"Failed to read file: {e}"
                )
        
        # Calculate metadata
        word_count = len(text.split())
        line_count = text.count("\n") + 1
        
        # Detect language (programming vs natural)
        lang = self._detect_language(text)
        
        return ExtractionResult(
            text=text,
            metadata={
                "word_count": word_count,
                "line_count": line_count,
                "language": lang,
                "programming_language": file_path.suffix.lower().lstrip("."),
                "file_type": "code",
            }
        )
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect natural language in comments/strings."""
        if not text or len(text.strip()) < 50:
            return None
        
        try:
            langdetect = _get_langdetect()
            # Extract comments and strings for language detection
            sample = text[:5000]
            return langdetect.detect(sample)
        except Exception:
            return None


class JSONExtractor(BaseExtractor):
    """Extractor for JSON files with pretty formatting."""
    
    SUPPORTED_EXTENSIONS = {".json"}
    
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract and format JSON content."""
        try:
            text = file_path.read_text(encoding="utf-8")
            # Parse and re-format for consistent output
            data = json.loads(text)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            
            word_count = len(formatted.split())
            
            return ExtractionResult(
                text=formatted,
                metadata={
                    "word_count": word_count,
                    "file_type": "json",
                    "keys_count": self._count_keys(data),
                }
            )
        except json.JSONDecodeError as e:
            return ExtractionResult(
                text=text if 'text' in dir() else "",
                success=False,
                error=f"Invalid JSON: {e}"
            )
        except Exception as e:
            return ExtractionResult(
                text="",
                success=False,
                error=f"Failed to read JSON: {e}"
            )
    
    def _count_keys(self, data: Any, count: int = 0) -> int:
        """Recursively count keys in JSON."""
        if isinstance(data, dict):
            count += len(data)
            for v in data.values():
                count = self._count_keys(v, count)
        elif isinstance(data, list):
            for item in data:
                count = self._count_keys(item, count)
        return count


class PDFExtractor(BaseExtractor):
    """Extractor for PDF files using pypdf."""
    
    SUPPORTED_EXTENSIONS = {".pdf"}
    
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text from PDF file."""
        try:
            pypdf = _get_pypdf()
        except ImportError:
            return ExtractionResult(
                text="",
                success=False,
                error="pypdf not installed. Run: uv pip install pypdf"
            )
        
        try:
            reader = pypdf.PdfReader(str(file_path))
            pages_text = []
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            
            text = "\n\n".join(pages_text)
            word_count = len(text.split())
            
            # Detect language
            language = self._detect_language(text)
            
            # Extract PDF metadata
            pdf_metadata = {}
            if reader.metadata:
                pdf_metadata = {
                    "title": reader.metadata.get("/Title"),
                    "author": reader.metadata.get("/Author"),
                    "subject": reader.metadata.get("/Subject"),
                    "creator": reader.metadata.get("/Creator"),
                }
                # Clean None values
                pdf_metadata = {k: v for k, v in pdf_metadata.items() if v}
            
            return ExtractionResult(
                text=text,
                metadata={
                    "word_count": word_count,
                    "pages": len(reader.pages),
                    "language": language,
                    "file_type": "pdf",
                    **pdf_metadata,
                }
            )
        except Exception as e:
            return ExtractionResult(
                text="",
                success=False,
                error=f"Failed to extract PDF: {e}"
            )
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        if not text or len(text.strip()) < 20:
            return None
        
        try:
            langdetect = _get_langdetect()
            sample = text[:5000]
            return langdetect.detect(sample)
        except Exception:
            return None


class DOCXExtractor(BaseExtractor):
    """Extractor for DOCX files using python-docx."""
    
    SUPPORTED_EXTENSIONS = {".docx"}
    
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text from DOCX file."""
        try:
            docx = _get_docx()
        except ImportError:
            return ExtractionResult(
                text="",
                success=False,
                error="python-docx not installed. Run: uv pip install python-docx"
            )
        
        try:
            doc = docx.Document(str(file_path))
            paragraphs = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        paragraphs.append(" | ".join(row_text))
            
            text = "\n\n".join(paragraphs)
            word_count = len(text.split())
            
            # Detect language
            language = self._detect_language(text)
            
            # Extract document properties
            doc_metadata = {}
            if doc.core_properties:
                props = doc.core_properties
                doc_metadata = {
                    "title": props.title,
                    "author": props.author,
                    "subject": props.subject,
                    "created": str(props.created) if props.created else None,
                    "modified": str(props.modified) if props.modified else None,
                }
                doc_metadata = {k: v for k, v in doc_metadata.items() if v}
            
            return ExtractionResult(
                text=text,
                metadata={
                    "word_count": word_count,
                    "paragraphs": len(paragraphs),
                    "tables": len(doc.tables),
                    "language": language,
                    "file_type": "docx",
                    **doc_metadata,
                }
            )
        except Exception as e:
            return ExtractionResult(
                text="",
                success=False,
                error=f"Failed to extract DOCX: {e}"
            )
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        if not text or len(text.strip()) < 20:
            return None
        
        try:
            langdetect = _get_langdetect()
            sample = text[:5000]
            return langdetect.detect(sample)
        except Exception:
            return None


class TextExtractor:
    """
    Main text extractor that delegates to specialized extractors.
    
    This is the primary interface for text extraction. It automatically
    selects the appropriate extractor based on file extension.
    
    Example:
        extractor = TextExtractor()
        result = extractor.extract("/path/to/document.pdf")
        if result.success:
            print(f"Text: {result.text[:100]}...")
            print(f"Language: {result.language}")
            print(f"Word count: {result.word_count}")
    """
    
    # Registry of extractors
    EXTRACTORS: list[Type[BaseExtractor]] = [
        PDFExtractor,
        DOCXExtractor,
        JSONExtractor,
        CodeExtractor,
        PlainTextExtractor,  # Must be last (fallback for .txt, .md, etc.)
    ]
    
    def __init__(self):
        """Initialize the text extractor."""
        self._extractors: Dict[str, BaseExtractor] = {}
        self._init_extractors()
    
    def _init_extractors(self):
        """Initialize extractor instances for each extension."""
        for extractor_class in self.EXTRACTORS:
            instance = extractor_class()
            for ext in extractor_class.SUPPORTED_EXTENSIONS:
                # First match wins (order matters)
                if ext not in self._extractors:
                    self._extractors[ext] = instance
    
    def extract(self, file_path: str | Path) -> ExtractionResult:
        """
        Extract text from a file.
        
        Args:
            file_path: Path to the file to extract text from.
            
        Returns:
            ExtractionResult with text and metadata.
        """
        path = Path(file_path)
        
        # Check file exists
        if not path.exists():
            return ExtractionResult(
                text="",
                success=False,
                error=f"File not found: {path}"
            )
        
        if not path.is_file():
            return ExtractionResult(
                text="",
                success=False,
                error=f"Not a file: {path}"
            )
        
        # Find appropriate extractor
        ext = path.suffix.lower()
        extractor = self._extractors.get(ext)
        
        if extractor is None:
            return ExtractionResult(
                text="",
                success=False,
                error=f"Unsupported file type: {ext}"
            )
        
        # Extract text
        try:
            result = extractor.extract(path)
            
            # Add common metadata
            result.metadata["file_path"] = str(path)
            result.metadata["file_name"] = path.name
            result.metadata["file_size"] = path.stat().st_size
            
            return result
        except Exception as e:
            logger.exception(f"Extraction failed for {path}")
            return ExtractionResult(
                text="",
                success=False,
                error=f"Extraction failed: {e}"
            )
    
    def get_supported_extensions(self) -> set:
        """Return set of all supported file extensions."""
        return set(self._extractors.keys())
    
    def can_extract(self, file_path: str | Path) -> bool:
        """Check if we can extract text from this file type."""
        path = Path(file_path)
        return path.suffix.lower() in self._extractors


# Convenience function
def extract_text(file_path: str | Path) -> ExtractionResult:
    """
    Extract text from a file (convenience function).
    
    Args:
        file_path: Path to the file.
        
    Returns:
        ExtractionResult with text and metadata.
    """
    extractor = TextExtractor()
    return extractor.extract(file_path)
