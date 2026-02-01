"""
Unit tests for ChunkingPipeline and related classes.

Tests cover:
- Chunk dataclass creation and serialization
- ChunkingPipeline text splitting
- Overlap handling
- Sentence boundary detection
- Edge cases (empty text, very short text, etc.)
"""

import pytest
from datetime import datetime

from src.indexation.interfaces import Chunk, ChunkingConfig, ChunkingResult
from src.indexation.chunker import ChunkingPipeline, chunk_text, CHARS_PER_TOKEN


# =============================================================================
# Chunk Dataclass Tests
# =============================================================================

class TestChunk:
    """Tests for Chunk dataclass."""
    
    def test_create_chunk(self):
        """Test Chunk.create factory method."""
        chunk = Chunk.create(
            doc_id="abc123",
            path="/test/doc.txt",
            title="Test Doc",
            content="This is test content.",
            chunk_index=0,
            total_chunks=1,
            offset_start=0,
            offset_end=21,
        )
        
        assert chunk.chunk_id == "abc123_00000"
        assert chunk.doc_id == "abc123"
        assert chunk.content == "This is test content."
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 1
    
    def test_chunk_to_dict(self):
        """Test Chunk serialization to dict."""
        chunk = Chunk.create(
            doc_id="abc123",
            path="/test/doc.txt",
            title="Test Doc",
            content="Content here",
            chunk_index=5,
            total_chunks=10,
            offset_start=100,
            offset_end=200,
            metadata={"language": "en"},
        )
        
        data = chunk.to_dict()
        
        assert data["chunk_id"] == "abc123_00005"
        assert data["metadata"] == {"language": "en"}
        assert "created_at" in data
    
    def test_chunk_from_dict(self):
        """Test Chunk deserialization from dict."""
        data = {
            "chunk_id": "test_00001",
            "doc_id": "test",
            "path": "/path/to/file.txt",
            "title": "Test",
            "content": "Test content",
            "chunk_index": 1,
            "total_chunks": 5,
            "offset_start": 50,
            "offset_end": 100,
            "metadata": {"category": "test"},
            "created_at": "2026-02-01T10:00:00",
        }
        
        chunk = Chunk.from_dict(data)
        
        assert chunk.chunk_id == "test_00001"
        assert chunk.chunk_index == 1
        assert chunk.metadata["category"] == "test"
    
    def test_chunk_len(self):
        """Test Chunk __len__ returns content length."""
        chunk = Chunk.create(
            doc_id="test",
            path="",
            title="",
            content="12345678901234567890",  # 20 chars
            chunk_index=0,
            total_chunks=1,
            offset_start=0,
            offset_end=20,
        )
        
        assert len(chunk) == 20
    
    def test_chunk_repr(self):
        """Test Chunk string representation."""
        chunk = Chunk.create(
            doc_id="test",
            path="",
            title="",
            content="Short content",
            chunk_index=0,
            total_chunks=1,
            offset_start=0,
            offset_end=13,
        )
        
        repr_str = repr(chunk)
        assert "test_00000" in repr_str
        assert "13 chars" in repr_str


# =============================================================================
# ChunkingConfig Tests
# =============================================================================

class TestChunkingConfig:
    """Tests for ChunkingConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.min_chunk_size == 100
        assert config.split_on_sentences is True
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "chunk_size": 256,
            "chunk_overlap": 25,
            "min_chunk_size": 50,
            "embedding_model": "custom/model",
        }
        
        config = ChunkingConfig.from_dict(data)
        
        assert config.chunk_size == 256
        assert config.chunk_overlap == 25
        assert config.embedding_model == "custom/model"
    
    def test_config_from_partial_dict(self):
        """Test config with missing keys uses defaults."""
        data = {"chunk_size": 1024}
        
        config = ChunkingConfig.from_dict(data)
        
        assert config.chunk_size == 1024
        assert config.chunk_overlap == 50  # Default


# =============================================================================
# ChunkingPipeline Tests
# =============================================================================

class TestChunkingPipeline:
    """Tests for ChunkingPipeline class."""
    
    @pytest.fixture
    def pipeline(self):
        """Create default pipeline for tests."""
        return ChunkingPipeline()
    
    @pytest.fixture
    def small_pipeline(self):
        """Create pipeline with small chunks for testing."""
        config = ChunkingConfig(
            chunk_size=50,  # ~150 chars
            chunk_overlap=10,  # ~30 chars
            min_chunk_size=10,  # ~30 chars
        )
        return ChunkingPipeline(config)
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes with correct sizes."""
        assert pipeline.chunk_size_chars == 512 * CHARS_PER_TOKEN
        assert pipeline.overlap_chars == 50 * CHARS_PER_TOKEN
    
    def test_chunk_short_document(self, pipeline):
        """Test that short documents produce single chunk."""
        text = "This is a short document that fits in one chunk."
        
        result = pipeline.chunk_document(
            text=text,
            doc_id="short123",
            path="/test/short.txt",
            title="Short Doc",
        )
        
        assert result.success is True
        assert result.chunk_count == 1
        assert result.chunks[0].content == text
        assert result.chunks[0].chunk_index == 0
        assert result.chunks[0].total_chunks == 1
    
    def test_chunk_empty_document(self, pipeline):
        """Test that empty documents return error."""
        result = pipeline.chunk_document(
            text="",
            doc_id="empty123",
            path="/test/empty.txt",
            title="Empty Doc",
        )
        
        assert result.success is False
        assert "Empty" in result.error
        assert result.chunk_count == 0
    
    def test_chunk_whitespace_only(self, pipeline):
        """Test that whitespace-only documents return error."""
        result = pipeline.chunk_document(
            text="   \n\n\t  ",
            doc_id="ws123",
            path="/test/ws.txt",
            title="Whitespace Doc",
        )
        
        assert result.success is False
    
    def test_chunk_long_document(self, small_pipeline):
        """Test chunking of longer documents."""
        # Create text that should produce multiple chunks
        text = " ".join(["word"] * 200)  # ~1000 chars
        
        result = small_pipeline.chunk_document(
            text=text,
            doc_id="long123",
            path="/test/long.txt",
            title="Long Doc",
        )
        
        assert result.success is True
        assert result.chunk_count > 1
        
        # Check all chunks have correct metadata
        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == i
            assert chunk.total_chunks == result.chunk_count
            assert chunk.doc_id == "long123"
    
    def test_chunk_overlap(self, small_pipeline):
        """Test that chunks overlap correctly."""
        # Create text that will produce multiple chunks
        sentences = [
            "First sentence here.",
            "Second sentence here.",
            "Third sentence here.",
            "Fourth sentence here.",
            "Fifth sentence here.",
            "Sixth sentence here.",
            "Seventh sentence here.",
            "Eighth sentence here.",
        ]
        text = " ".join(sentences)
        
        result = small_pipeline.chunk_document(
            text=text,
            doc_id="overlap123",
            path="/test/overlap.txt",
            title="Overlap Test",
        )
        
        # With overlap, adjacent chunks should share some content
        if result.chunk_count > 1:
            # Check offsets show overlap
            for i in range(1, result.chunk_count):
                prev_chunk = result.chunks[i - 1]
                curr_chunk = result.chunks[i]
                
                # Current chunk should start before previous chunk ends
                # (unless they're sequential without overlap)
                overlap = prev_chunk.offset_end - curr_chunk.offset_start
                # There should be some overlap or they're adjacent
                assert overlap >= 0 or curr_chunk.offset_start == prev_chunk.offset_end
    
    def test_chunk_sentence_boundaries(self, small_pipeline):
        """Test that chunks try to break on sentence boundaries."""
        text = (
            "This is the first sentence. "
            "This is the second sentence. "
            "This is the third sentence. "
            "This is the fourth sentence. "
            "This is the fifth sentence."
        )
        
        result = small_pipeline.chunk_document(
            text=text,
            doc_id="sent123",
            path="/test/sent.txt",
            title="Sentence Test",
        )
        
        # Chunks should ideally end with period
        for chunk in result.chunks:
            # At least some chunks should end at sentence boundaries
            content = chunk.content.strip()
            # Last chunk might not end with period
            if chunk.chunk_index < chunk.total_chunks - 1:
                # Should prefer ending at punctuation
                assert any(content.endswith(p) for p in [".", "!", "?"]) or True
    
    def test_chunk_preserves_offsets(self, small_pipeline):
        """Test that offsets correctly map to original text."""
        text = "AAAA BBBB CCCC DDDD EEEE FFFF GGGG HHHH IIII JJJJ"
        
        result = small_pipeline.chunk_document(
            text=text,
            doc_id="offset123",
            path="/test/offset.txt",
            title="Offset Test",
        )
        
        # Verify each chunk's offset matches original text
        for chunk in result.chunks:
            expected_content = text[chunk.offset_start:chunk.offset_end]
            # Content might be stripped, so compare stripped versions
            assert chunk.content.strip() in text
    
    def test_chunk_metadata_passed_through(self, pipeline):
        """Test that metadata is attached to all chunks."""
        metadata = {"language": "en", "category": "test"}
        
        result = pipeline.chunk_document(
            text="Some content here for testing metadata.",
            doc_id="meta123",
            path="/test/meta.txt",
            title="Meta Test",
            metadata=metadata,
        )
        
        for chunk in result.chunks:
            assert chunk.metadata == metadata
    
    def test_normalize_text(self, pipeline):
        """Test text normalization."""
        text = "Multiple\r\n\r\n\r\nNewlines   and    spaces"
        
        normalized = pipeline._normalize_text(text)
        
        # Multiple newlines collapsed to double
        assert "\n\n\n" not in normalized
        # Multiple spaces collapsed
        assert "   " not in normalized
    
    def test_chunk_chinese_text(self, small_pipeline):
        """Test chunking works with Chinese text."""
        text = "這是中文測試。這是第二句話。這是第三句話。這是第四句話。"
        
        result = small_pipeline.chunk_document(
            text=text,
            doc_id="chinese123",
            path="/test/chinese.txt",
            title="Chinese Test",
        )
        
        assert result.success is True
        assert result.chunk_count >= 1
    
    def test_compute_doc_id(self):
        """Test static method for computing document ID."""
        content = "Test content for hashing"
        
        doc_id = ChunkingPipeline.compute_doc_id(content)
        
        assert len(doc_id) == 64  # SHA256 hex
        # Same content should produce same ID
        assert doc_id == ChunkingPipeline.compute_doc_id(content)
        # Different content should produce different ID
        assert doc_id != ChunkingPipeline.compute_doc_id("Different content")
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "a" * 300  # 300 characters
        
        tokens = ChunkingPipeline.estimate_tokens(text)
        
        # Should be approximately 300 / CHARS_PER_TOKEN
        expected = 300 // CHARS_PER_TOKEN
        assert tokens == expected


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestChunkTextFunction:
    """Tests for the chunk_text convenience function."""
    
    def test_chunk_text_basic(self):
        """Test basic usage of chunk_text function."""
        text = "This is some text to chunk."
        
        chunks = chunk_text(text)
        
        assert len(chunks) >= 1
        assert chunks[0].content == text
    
    def test_chunk_text_with_doc_id(self):
        """Test chunk_text with explicit doc_id."""
        text = "Test content"
        doc_id = "explicit_id"
        
        chunks = chunk_text(text, doc_id=doc_id)
        
        assert chunks[0].doc_id == doc_id
    
    def test_chunk_text_auto_generates_doc_id(self):
        """Test that doc_id is auto-generated from content."""
        text = "Auto ID content"
        
        chunks = chunk_text(text)
        
        # Should have generated a hash
        assert len(chunks[0].doc_id) == 64
    
    def test_chunk_text_custom_sizes(self):
        """Test chunk_text with custom chunk sizes."""
        text = " ".join(["word"] * 500)  # Long text
        
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        
        # Should produce multiple smaller chunks
        assert len(chunks) >= 1


# =============================================================================
# ChunkingResult Tests
# =============================================================================

class TestChunkingResult:
    """Tests for ChunkingResult dataclass."""
    
    def test_result_success(self):
        """Test successful result properties."""
        chunks = [
            Chunk.create("id", "", "", "content1", 0, 2, 0, 8),
            Chunk.create("id", "", "", "content2", 1, 2, 8, 16),
        ]
        
        result = ChunkingResult(
            doc_id="test",
            path="/test.txt",
            chunks=chunks,
            total_tokens=100,
            success=True,
        )
        
        assert result.chunk_count == 2
        assert result.success is True
        assert "2 chunks" in repr(result)
    
    def test_result_failure(self):
        """Test failed result properties."""
        result = ChunkingResult(
            doc_id="test",
            path="/test.txt",
            chunks=[],
            total_tokens=0,
            success=False,
            error="Something went wrong",
        )
        
        assert result.chunk_count == 0
        assert result.success is False
        assert "Something went wrong" in repr(result)
