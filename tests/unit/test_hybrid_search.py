"""
Unit tests for HybridSearchEngine.

Tests cover:
- Engine initialization
- SearchFilter dataclass
- Score normalization
- Result merging with weights
- Parallel search execution
- Search modes (hybrid, semantic, fulltext)
- Edge cases and error handling
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# ============================================================================
# Mock Setup (before importing HybridSearchEngine)
# ============================================================================

# Create mock logger
mock_logger = Mock()
mock_logger.info = Mock()
mock_logger.warning = Mock()
mock_logger.debug = Mock()
mock_logger.error = Mock()

mock_get_logger = Mock(return_value=mock_logger)

# Mock logger module
mock_logger_module = Mock()
mock_logger_module.get_logger = mock_get_logger

# Insert mock before import
sys.modules["src.core.logger"] = mock_logger_module


# ============================================================================
# Import after mocking
# ============================================================================

from src.search.hybrid_engine import (
    HybridSearchEngine,
    SearchFilter,
    SearchResult,
    HybridSearchResponse,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create a HybridSearchEngine instance with mocked clients."""
    eng = HybridSearchEngine(semantic_weight=0.6, max_workers=2)
    # Don't initialize clients - they'll be mocked per test
    eng._lancedb_client = None
    eng._meilisearch_client = None
    return eng


@pytest.fixture
def sample_lancedb_results():
    """Sample results from LanceDB."""
    return [
        {
            "id": "abc123",
            "path": "/docs/report.pdf",
            "title": "Annual Report",
            "content": "Financial performance summary...",
            "category": "finance",
            "language": "en",
            "_score": 0.95,
        },
        {
            "id": "def456",
            "path": "/docs/invoice.pdf",
            "title": "Invoice 2025",
            "content": "Payment details...",
            "category": "finance",
            "language": "en",
            "_score": 0.82,
        },
    ]


@pytest.fixture
def sample_meilisearch_results():
    """Sample results from Meilisearch."""
    return [
        {
            "id": "def456",  # Same as LanceDB result 2
            "path": "/docs/invoice.pdf",
            "title": "Invoice 2025",
            "content": "Payment details for Q1...",
            "category": "finance",
            "language": "en",
            "_highlights": {"title": "<em>Invoice</em> 2025"},
        },
        {
            "id": "ghi789",
            "path": "/docs/contract.pdf",
            "title": "Contract Agreement",
            "content": "Terms and conditions...",
            "category": "legal",
            "language": "en",
            "_highlights": {},
        },
    ]


# ============================================================================
# SearchFilter Tests
# ============================================================================

class TestSearchFilter:
    """Tests for SearchFilter dataclass."""
    
    def test_default_values(self):
        """Test default filter values."""
        f = SearchFilter()
        assert f.path_contains is None
        assert f.category is None
        assert f.language is None
        assert f.date_after is None
        assert f.date_before is None
        assert f.file_types is None
    
    def test_custom_values(self):
        """Test filter with custom values."""
        now = datetime.now()
        f = SearchFilter(
            path_contains="documents",
            category="finance",
            language="fr",
            date_after=now,
            file_types=[".pdf", ".docx"],
        )
        assert f.path_contains == "documents"
        assert f.category == "finance"
        assert f.language == "fr"
        assert f.date_after == now
        assert f.file_types == [".pdf", ".docx"]


# ============================================================================
# SearchResult Tests
# ============================================================================

class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_minimal_result(self):
        """Test result with required fields only."""
        r = SearchResult(
            id="abc123",
            path="/docs/test.pdf",
            title="Test Document",
            content="Test content...",
            score=0.85,
        )
        assert r.id == "abc123"
        assert r.score == 0.85
        assert r.semantic_score == 0.0
        assert r.fulltext_score == 0.0
    
    def test_full_result(self):
        """Test result with all fields."""
        now = datetime.now()
        r = SearchResult(
            id="abc123",
            path="/docs/test.pdf",
            title="Test Document",
            content="Test content...",
            score=0.85,
            semantic_score=0.9,
            fulltext_score=0.7,
            category="test",
            language="en",
            file_size=1024,
            modified_at=now,
            metadata={"key": "value"},
        )
        assert r.semantic_score == 0.9
        assert r.fulltext_score == 0.7
        assert r.metadata == {"key": "value"}


# ============================================================================
# HybridSearchEngine Initialization Tests
# ============================================================================

class TestHybridSearchEngineInit:
    """Tests for engine initialization."""
    
    def test_default_weights(self):
        """Test default semantic/fulltext weights."""
        eng = HybridSearchEngine()
        assert eng.semantic_weight == 0.6
        assert eng.fulltext_weight == pytest.approx(0.4)
    
    def test_custom_weights(self):
        """Test custom weights."""
        eng = HybridSearchEngine(semantic_weight=0.7)
        assert eng.semantic_weight == 0.7
        assert eng.fulltext_weight == pytest.approx(0.3)
    
    def test_max_workers(self):
        """Test max workers configuration."""
        eng = HybridSearchEngine(max_workers=4)
        assert eng.max_workers == 4


# ============================================================================
# Score Normalization Tests
# ============================================================================

class TestScoreNormalization:
    """Tests for score normalization."""
    
    def test_normalize_valid_score(self, engine):
        """Test normalizing a valid 0-1 score."""
        score = engine._normalize_score(0.75, rank=0, total=10)
        assert score == 0.75
    
    def test_normalize_out_of_range_score(self, engine):
        """Test that out-of-range scores get converted."""
        # Score > 1 is treated as distance
        score = engine._normalize_score(2.0, rank=0, total=10)
        assert score == pytest.approx(1.0 / 3.0)  # 1/(1+2)
    
    def test_normalize_rank_based(self, engine):
        """Test rank-based scoring when no score provided."""
        # First result should get highest score
        score = engine._normalize_score(None, rank=0, total=10)
        assert score == 1.0
        
        # Last result should get lowest
        score = engine._normalize_score(None, rank=9, total=10)
        assert score == pytest.approx(0.1)
    
    def test_normalize_single_result(self, engine):
        """Test scoring with single result."""
        score = engine._normalize_score(None, rank=0, total=1)
        assert score == 1.0


# ============================================================================
# Result Merging Tests
# ============================================================================

class TestResultMerging:
    """Tests for result merging logic."""
    
    def test_merge_empty_results(self, engine):
        """Test merging empty result sets."""
        results = engine._merge_results([], [], limit=10)
        assert results == []
    
    def test_merge_lancedb_only(self, engine, sample_lancedb_results):
        """Test merging with only LanceDB results."""
        results = engine._merge_results(sample_lancedb_results, [], limit=10)
        
        assert len(results) == 2
        # First should have higher score
        assert results[0].score >= results[1].score
        # Only semantic scores should be non-zero
        assert results[0].semantic_score > 0
        assert results[0].fulltext_score == 0
    
    def test_merge_meilisearch_only(self, engine, sample_meilisearch_results):
        """Test merging with only Meilisearch results."""
        results = engine._merge_results([], sample_meilisearch_results, limit=10)
        
        assert len(results) == 2
        # Only fulltext scores should be non-zero
        assert results[0].fulltext_score > 0
        assert results[0].semantic_score == 0
    
    def test_merge_combined(self, engine, sample_lancedb_results, sample_meilisearch_results):
        """Test merging results from both sources."""
        results = engine._merge_results(
            sample_lancedb_results,
            sample_meilisearch_results,
            limit=10
        )
        
        # Should have 3 unique documents (one overlap: def456)
        assert len(results) == 3
        
        # Find the overlapping document
        overlap = next((r for r in results if r.id == "def456"), None)
        assert overlap is not None
        # Should have both scores
        assert overlap.semantic_score > 0
        assert overlap.fulltext_score > 0
        # Combined score should have overlap boost
        assert overlap.score > overlap.semantic_score * 0.6 + overlap.fulltext_score * 0.4
    
    def test_merge_respects_limit(self, engine, sample_lancedb_results):
        """Test that merge respects the limit."""
        results = engine._merge_results(sample_lancedb_results, [], limit=1)
        assert len(results) == 1
    
    def test_merge_score_weights(self, engine, sample_lancedb_results, sample_meilisearch_results):
        """Test that weights are applied correctly."""
        # Use only non-overlapping documents for this test
        lance_only = [sample_lancedb_results[0]]  # abc123
        meili_only = [sample_meilisearch_results[1]]  # ghi789
        
        results = engine._merge_results(lance_only, meili_only, limit=10)
        
        for r in results:
            if r.semantic_score > 0 and r.fulltext_score == 0:
                # Semantic only: score = semantic * 0.6
                expected = r.semantic_score * engine.semantic_weight
                assert abs(r.score - expected) < 0.01
            elif r.fulltext_score > 0 and r.semantic_score == 0:
                # Fulltext only: score = fulltext * 0.4
                expected = r.fulltext_score * engine.fulltext_weight
                assert abs(r.score - expected) < 0.01


# ============================================================================
# Parallel Search Tests
# ============================================================================

class TestParallelSearch:
    """Tests for parallel search execution."""
    
    def test_search_parallel_hybrid(self, engine, sample_lancedb_results, sample_meilisearch_results):
        """Test parallel search in hybrid mode."""
        # Mock the sync search methods
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=(sample_meilisearch_results, 30.0))
        
        # Use search_sync which handles event loop
        response = engine.search_sync(query="test", limit=10, mode="hybrid")
        
        assert response.lancedb_count == 2
        assert response.meilisearch_count == 2
    
    def test_search_parallel_semantic_only(self, engine, sample_lancedb_results):
        """Test parallel search in semantic mode (LanceDB only)."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        response = engine.search_sync(query="test", limit=10, mode="semantic")
        
        assert response.lancedb_count == 2
        assert response.meilisearch_count == 0


# ============================================================================
# Full Search Tests
# ============================================================================

class TestFullSearch:
    """Tests for complete search workflow."""
    
    def test_search_empty_query(self, engine):
        """Test search with empty query."""
        response = engine.search_sync(query="", limit=10)
        
        assert response.query == ""
        assert response.total == 0
        assert response.results == []
    
    def test_search_whitespace_query(self, engine):
        """Test search with whitespace-only query."""
        response = engine.search_sync(query="   ", limit=10)
        
        assert response.total == 0
    
    def test_search_with_results(self, engine, sample_lancedb_results, sample_meilisearch_results):
        """Test search returning results."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=(sample_meilisearch_results, 30.0))
        
        response = engine.search_sync(query="invoice", limit=10)
        
        assert response.query == "invoice"
        assert response.total == 3  # 3 unique docs
        assert response.lancedb_count == 2
        assert response.meilisearch_count == 2
        assert response.mode == "hybrid"
        assert response.search_time_ms > 0
    
    def test_search_with_filters(self, engine, sample_lancedb_results):
        """Test search with filters applied."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        filters = SearchFilter(category="finance", language="en")
        response = engine.search_sync(query="report", limit=10, filters=filters)
        
        # Verify search was called (we trust the engine to pass filters)
        assert engine._search_lancedb_sync.called
    
    def test_search_pagination(self, engine, sample_lancedb_results):
        """Test search with offset."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        response = engine.search_sync(query="test", limit=1, offset=1)
        
        assert len(response.results) <= 1
    
    def test_search_mode_semantic(self, engine, sample_lancedb_results):
        """Test semantic-only search mode."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        response = engine.search_sync(query="test", limit=10, mode="semantic")
        
        assert response.mode == "semantic"
        # All results should have fulltext_score == 0
        for r in response.results:
            assert r.fulltext_score == 0.0
    
    def test_search_mode_fulltext(self, engine, sample_meilisearch_results):
        """Test fulltext-only search mode."""
        engine._search_lancedb_sync = Mock(return_value=([], 0.0))
        engine._search_meilisearch_sync = Mock(return_value=(sample_meilisearch_results, 30.0))
        
        response = engine.search_sync(query="test", limit=10, mode="fulltext")
        
        assert response.mode == "fulltext"


# ============================================================================
# Sync Search Tests
# ============================================================================

class TestSyncSearch:
    """Tests for synchronous search method."""
    
    def test_search_sync(self, engine, sample_lancedb_results):
        """Test synchronous search wrapper."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        response = engine.search_sync(query="test", limit=10)
        
        assert response.query == "test"
        assert len(response.results) == 2


# ============================================================================
# Response Structure Tests
# ============================================================================

class TestHybridSearchResponse:
    """Tests for HybridSearchResponse structure."""
    
    def test_response_fields(self):
        """Test response has all required fields."""
        response = HybridSearchResponse(
            query="test query",
            results=[],
            total=0,
        )
        
        assert response.query == "test query"
        assert response.results == []
        assert response.total == 0
        assert response.lancedb_count == 0
        assert response.meilisearch_count == 0
        assert response.search_time_ms == 0.0
        assert response.mode == "hybrid"
    
    def test_response_with_results(self, sample_lancedb_results):
        """Test response with results."""
        results = [
            SearchResult(
                id="abc",
                path="/test",
                title="Test",
                content="...",
                score=0.9,
            )
        ]
        
        response = HybridSearchResponse(
            query="test",
            results=results,
            total=1,
            lancedb_count=1,
            meilisearch_count=0,
            search_time_ms=50.0,
            lancedb_time_ms=45.0,
            meilisearch_time_ms=0.0,
            mode="semantic",
        )
        
        assert len(response.results) == 1
        assert response.lancedb_time_ms == 45.0


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_search_both_clients_fail(self, engine):
        """Test graceful handling when clients fail."""
        # Mock clients that return empty results (simulating failure)
        engine._search_lancedb_sync = Mock(return_value=([], 0.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        response = engine.search_sync(query="test", limit=10)
        
        assert response.total == 0
    
    def test_search_partial_failure(self, engine, sample_lancedb_results):
        """Test when one client fails but other works."""
        engine._search_lancedb_sync = Mock(return_value=(sample_lancedb_results, 50.0))
        engine._search_meilisearch_sync = Mock(return_value=([], 0.0))
        
        response = engine.search_sync(query="test", limit=10)
        
        # Should still return LanceDB results
        assert response.lancedb_count == 2
    
    def test_cleanup(self, engine):
        """Test engine cleanup."""
        engine.close()
        # Should not raise
