"""
Unit tests for RAGEngine.

Tests cover:
- Initialization and configuration
- Context search functionality
- Prompt enrichment
- Token estimation and truncation
- Context formatting
- Chat message enrichment
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from src.llm.rag_engine import (
    RAGEngine,
    RAGResult,
    ContextDocument,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Mock ConfigManager with RAG configuration."""
    config = Mock()
    config.get_section.return_value = {
        "max_context_docs": 5,
        "context_max_tokens": 2000,
        "min_relevance_score": 0.3,
        "include_metadata": True,
    }
    return config


@pytest.fixture
def mock_config_defaults():
    """Mock ConfigManager with no RAG section (use defaults)."""
    config = Mock()
    config.get_section.return_value = None
    return config


@pytest.fixture
def mock_logger():
    """Mock StructuredLogger."""
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def rag_engine(mock_config, mock_logger):
    """Create RAGEngine with mocked dependencies."""
    return RAGEngine(mock_config, mock_logger)


@pytest.fixture
def sample_search_results():
    """Sample search results for mocking HybridSearchEngine."""
    @dataclass
    class MockSearchResult:
        id: str
        path: str
        title: str
        content: str
        score: float
        category: str = None
        language: str = None
        metadata: dict = None
        
        def __post_init__(self):
            if self.metadata is None:
                self.metadata = {}
    
    @dataclass
    class MockSearchResponse:
        results: list
        search_time_ms: float = 50.0
    
    results = [
        MockSearchResult(
            id="abc123",
            path="/docs/report.pdf",
            title="Annual Report 2025",
            content="This is the annual financial report with detailed analysis...",
            score=0.95,
            category="finance",
            language="en",
        ),
        MockSearchResult(
            id="def456",
            path="/docs/manual.md",
            title="User Manual",
            content="Installation guide and usage instructions for the system...",
            score=0.72,
            category="documentation",
            language="en",
        ),
        MockSearchResult(
            id="ghi789",
            path="/code/utils.py",
            title="Utility Functions",
            content="def parse_data(input): # Parses input data...",
            score=0.45,
            category="code",
            language="en",
        ),
    ]
    
    return MockSearchResponse(results=results)


# ============================================================================
# Initialization Tests
# ============================================================================

class TestRAGEngineInit:
    """Test RAGEngine initialization."""
    
    def test_init_with_config(self, mock_config, mock_logger):
        """Test initialization loads config correctly."""
        engine = RAGEngine(mock_config, mock_logger)
        
        assert engine.max_context_docs == 5
        assert engine.context_max_tokens == 2000
        assert engine.min_relevance_score == 0.3
        assert engine.include_metadata is True
        mock_logger.info.assert_called()
    
    def test_init_with_defaults(self, mock_config_defaults, mock_logger):
        """Test initialization uses defaults when no config."""
        engine = RAGEngine(mock_config_defaults, mock_logger)
        
        assert engine.max_context_docs == RAGEngine.DEFAULT_MAX_CONTEXT_DOCS
        assert engine.context_max_tokens == RAGEngine.DEFAULT_CONTEXT_MAX_TOKENS
        assert engine.min_relevance_score == RAGEngine.DEFAULT_MIN_RELEVANCE_SCORE
    
    def test_search_engine_lazy_load(self, rag_engine):
        """Test search engine is lazily loaded."""
        assert rag_engine._search_engine is None


# ============================================================================
# Token Estimation Tests
# ============================================================================

class TestTokenEstimation:
    """Test token estimation functionality."""
    
    def test_estimate_tokens(self, rag_engine):
        """Test token estimation from text."""
        text = "This is a test string with about forty characters."
        tokens = rag_engine._estimate_tokens(text)
        
        # ~50 chars / 4 chars per token = ~12 tokens
        assert 10 <= tokens <= 15
    
    def test_truncate_to_tokens(self, rag_engine):
        """Test text truncation to token limit."""
        long_text = "A" * 1000  # 1000 chars = ~250 tokens
        truncated = rag_engine._truncate_to_tokens(long_text, 50)
        
        # 50 tokens * 4 chars = 200 chars + "..."
        assert len(truncated) <= 210
        assert truncated.endswith("...")
    
    def test_truncate_short_text(self, rag_engine):
        """Test no truncation for short text."""
        short_text = "Hello world"
        result = rag_engine._truncate_to_tokens(short_text, 100)
        
        assert result == short_text


# ============================================================================
# Context Formatting Tests
# ============================================================================

class TestContextFormatting:
    """Test context document formatting."""
    
    def test_format_context_document(self, rag_engine):
        """Test single document formatting."""
        doc = ContextDocument(
            id="abc123",
            path="/docs/test.pdf",
            title="Test Document",
            content="This is test content.",
            score=0.85,
            category="test",
        )
        
        formatted = rag_engine._format_context_document(doc, 1)
        
        assert "[1] Test Document" in formatted
        assert "Path: /docs/test.pdf" in formatted
        assert "Category: test" in formatted
        assert "Relevance: 85%" in formatted
        assert "Content: This is test content" in formatted
    
    def test_format_without_metadata(self, mock_config, mock_logger):
        """Test formatting with metadata disabled."""
        mock_config.get_section.return_value = {
            "include_metadata": False,
        }
        engine = RAGEngine(mock_config, mock_logger)
        
        doc = ContextDocument(
            id="abc123",
            path="/docs/test.pdf",
            title="Test Document",
            content="Content here",
            score=0.85,
        )
        
        formatted = engine._format_context_document(doc, 1)
        
        assert "[1] Test Document" in formatted
        assert "Path:" not in formatted
        assert "Relevance:" not in formatted
    
    def test_build_context_section_empty(self, rag_engine):
        """Test context section with no documents."""
        section = rag_engine._build_context_section([])
        assert section == ""
    
    def test_build_context_section(self, rag_engine):
        """Test building context section with documents."""
        docs = [
            ContextDocument(
                id="1",
                path="/a.txt",
                title="Doc A",
                content="Content A",
                score=0.9,
            ),
            ContextDocument(
                id="2",
                path="/b.txt",
                title="Doc B",
                content="Content B",
                score=0.7,
            ),
        ]
        
        section = rag_engine._build_context_section(docs)
        
        assert "CONTEXT FROM YOUR DOCUMENTS" in section
        assert "[1] Doc A" in section
        assert "[2] Doc B" in section
        assert "END OF CONTEXT (2 documents)" in section


# ============================================================================
# Search Context Tests
# ============================================================================

class TestSearchContext:
    """Test context search functionality."""
    
    def test_search_context_success(self, rag_engine, sample_search_results):
        """Test successful context search."""
        # Mock the search engine
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        docs = rag_engine.search_context("find financial report")
        
        # Should filter by min_relevance_score (0.3)
        assert len(docs) == 3  # All 3 have score > 0.3
        assert docs[0].score == 0.95
        assert docs[0].title == "Annual Report 2025"
    
    def test_search_context_filters_low_scores(self, rag_engine, sample_search_results):
        """Test that low-score results are filtered."""
        # Modify to have one below threshold
        sample_search_results.results[2].score = 0.2  # Below 0.3
        
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        docs = rag_engine.search_context("query")
        
        assert len(docs) == 2  # One filtered out
    
    def test_search_context_with_filters(self, rag_engine, sample_search_results):
        """Test search with category filter."""
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        docs = rag_engine.search_context(
            "query",
            filters={"category": "finance"},
        )
        
        # Verify filter was passed
        call_args = mock_search.search_sync.call_args
        assert call_args.kwargs["filters"] is not None
    
    def test_search_context_error_handling(self, rag_engine, mock_logger):
        """Test graceful handling of search errors."""
        mock_search = Mock()
        mock_search.search_sync.side_effect = Exception("Search failed")
        rag_engine._search_engine = mock_search
        
        # Should not raise, should return empty list
        docs = rag_engine.search_context("query")
        
        assert docs == []
        mock_logger.error.assert_called()


# ============================================================================
# Prompt Enrichment Tests
# ============================================================================

class TestEnrichPrompt:
    """Test prompt enrichment functionality."""
    
    def test_enrich_prompt_basic(self, rag_engine, sample_search_results):
        """Test basic prompt enrichment."""
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        result = rag_engine.enrich_prompt("What is in the annual report?")
        
        assert isinstance(result, RAGResult)
        assert result.original_prompt == "What is in the annual report?"
        assert "CONTEXT FROM YOUR DOCUMENTS" in result.enriched_prompt
        assert "What is in the annual report?" in result.enriched_prompt
        assert len(result.context_docs) > 0
        assert result.search_time_ms >= 0
    
    def test_enrich_prompt_no_context(self, rag_engine):
        """Test enrichment when no context found."""
        # Mock empty results
        mock_response = Mock()
        mock_response.results = []
        mock_response.search_time_ms = 10.0
        
        mock_search = Mock()
        mock_search.search_sync.return_value = mock_response
        rag_engine._search_engine = mock_search
        
        result = rag_engine.enrich_prompt("Random query")
        
        assert result.original_prompt == "Random query"
        assert result.enriched_prompt == "Random query"  # No context added
        assert len(result.context_docs) == 0
    
    def test_enrich_prompt_with_system_instruction(self, rag_engine, sample_search_results):
        """Test enrichment with system instruction."""
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        result = rag_engine.enrich_prompt(
            "What is the revenue?",
            system_instruction="You are a financial analyst.",
        )
        
        assert "You are a financial analyst." in result.enriched_prompt
        assert result.enriched_prompt.startswith("You are a financial analyst.")


# ============================================================================
# Chat Message Enrichment Tests
# ============================================================================

class TestEnrichMessages:
    """Test chat message enrichment."""
    
    def test_enrich_messages_basic(self, rag_engine, sample_search_results):
        """Test enriching chat messages."""
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is the annual report about?"},
        ]
        
        enriched, docs, time_ms = rag_engine.enrich_messages(messages)
        
        assert len(enriched) == 2
        assert enriched[0]["content"] == "You are helpful."  # Unchanged
        assert "CONTEXT FROM YOUR DOCUMENTS" in enriched[1]["content"]
        assert len(docs) > 0
    
    def test_enrich_messages_empty(self, rag_engine):
        """Test with empty messages."""
        enriched, docs, time_ms = rag_engine.enrich_messages([])
        
        assert enriched == []
        assert docs == []
        assert time_ms == 0.0
    
    def test_enrich_messages_no_user_message(self, rag_engine):
        """Test with no user message."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "assistant", "content": "Hello!"},
        ]
        
        enriched, docs, time_ms = rag_engine.enrich_messages(messages)
        
        assert enriched == messages  # Unchanged
        assert docs == []
    
    def test_enrich_messages_multi_turn(self, rag_engine, sample_search_results):
        """Test enrichment preserves conversation history."""
        mock_search = Mock()
        mock_search.search_sync.return_value = sample_search_results
        rag_engine._search_engine = mock_search
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Tell me about the report"},
        ]
        
        enriched, docs, time_ms = rag_engine.enrich_messages(messages)
        
        # First two messages unchanged
        assert enriched[0]["content"] == "Hello"
        assert enriched[1]["content"] == "Hi there!"
        # Last user message enriched
        assert "CONTEXT FROM YOUR DOCUMENTS" in enriched[2]["content"]
