"""
E2E Test: RAG Chunk Retrieval for Trump July 4th Event.

This test validates that the chunking pipeline correctly retrieves
the relevant chunk containing the July 4th, 2025 Trump event from
a large document (US-023 fix for context truncation issue).

The original bug: RAG returned "je n'ai pas trouvé de mention du 4 juillet"
despite the document containing this exact information. This was caused by
context_max_tokens: 2000 truncating 285K token documents to 0.7%.

The fix: Split documents into ~512 token chunks with semantic search,
so the LLM receives the most relevant passages, not random excerpts.
"""

import pytest
from typing import Optional

# Test document ID (Trump tariff analysis PDF)
TRUMP_DOC_ID = "2b584c924733244fc99f61535d17c126beddba8f5e82b6fe511b2d120b4b7744"


class TestChunkRetrieval:
    """Test that chunk search finds relevant passages."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize search engine."""
        from src.search.hybrid_engine import HybridSearchEngine
        self.engine = HybridSearchEngine()
    
    def test_chunk_search_finds_july_4th_event(self):
        """
        CRITICAL TEST: Verify that searching for "Trump 4 juillet 2025"
        returns chunks containing the actual July 4th event.
        
        Expected: At least one chunk should contain "7月4日" (July 4 in Chinese)
        or reference to Trump signing an act on July 4th.
        """
        response = self.engine.search_chunks(
            query="Trump 4 juillet 2025 événement",
            limit=10,
            min_score=0.3,
        )
        
        # Should find chunks
        assert response.total > 0, "No chunks found for July 4th query"
        
        # At least one chunk should contain July 4th reference
        july_4_found = False
        july_4_content = None
        
        for chunk in response.chunks:
            content = chunk.content.lower()
            # Check for various July 4th representations
            if any([
                "7月4日" in chunk.content,  # Chinese date
                "july 4" in content,
                "4 juillet" in content,
                "juillet 2025" in content,
            ]):
                july_4_found = True
                july_4_content = chunk.content[:200]
                break
        
        assert july_4_found, (
            f"No chunk contains July 4th reference. "
            f"Found {response.total} chunks but none with July 4th. "
            f"First chunk: {response.chunks[0].content[:100] if response.chunks else 'N/A'}"
        )
    
    def test_chunk_search_returns_scores_above_threshold(self):
        """Verify that returned chunks have valid scores."""
        response = self.engine.search_chunks(
            query="Trump tariff policy",
            limit=5,
            min_score=0.3,
        )
        
        for chunk in response.chunks:
            assert 0.3 <= chunk.score <= 1.0, (
                f"Chunk score {chunk.score} outside valid range [0.3, 1.0]"
            )
    
    def test_chunk_search_returns_unique_docs_count(self):
        """Verify unique_docs is correctly calculated."""
        response = self.engine.search_chunks(
            query="économie commerce",
            limit=10,
            min_score=0.2,
        )
        
        # unique_docs should be <= total chunks
        assert response.unique_docs <= response.total
        
        # Verify by counting manually
        doc_ids = set(chunk.doc_id for chunk in response.chunks)
        assert response.unique_docs == len(doc_ids)


class TestRAGWithChunks:
    """Test that RAGEngine uses chunks correctly."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize RAG engine."""
        from src.core.config import ConfigManager
        from src.core.logger import get_logger
        from src.llm.rag_engine import RAGEngine
        
        self.config = ConfigManager()
        self.logger = get_logger("test_rag")
        self.rag = RAGEngine(self.config, self.logger)
    
    def test_rag_uses_chunks_by_default(self):
        """Verify RAG engine uses chunk mode by default."""
        assert self.rag.use_chunks is True, (
            "RAG should use chunks by default (config: rag.use_chunks)"
        )
    
    def test_rag_enrich_prompt_with_chunks(self):
        """Test that enrich_prompt uses chunks and finds July 4th content."""
        result = self.rag.enrich_prompt(
            prompt="Quel événement s'est passé le 4 juillet 2025 concernant Trump?",
            max_context_chunks=5,
        )
        
        # Should use chunks mode
        assert result.mode == "chunks", (
            f"Expected mode='chunks', got mode='{result.mode}'"
        )
        
        # Should have context chunks
        assert len(result.context_chunks) > 0, "No context chunks returned"
        
        # Enriched prompt should contain context
        assert "CONTEXT FROM YOUR DOCUMENTS" in result.enriched_prompt
        assert result.total_context_tokens > 0
    
    def test_rag_chunks_contain_relevant_content(self):
        """Verify that RAG context chunks contain July 4th information."""
        result = self.rag.enrich_prompt(
            prompt="Trump 4 juillet 2025",
            max_context_chunks=10,
        )
        
        if result.mode != "chunks":
            pytest.skip("Chunks not available, skipping chunk content test")
        
        # Check if any chunk contains July 4th reference
        found = False
        for chunk in result.context_chunks:
            if "7月4日" in chunk.content or "juillet" in chunk.content.lower():
                found = True
                break
        
        assert found, (
            "RAG context chunks should contain July 4th reference. "
            f"Got {len(result.context_chunks)} chunks but none with July 4th."
        )


class TestChunkStore:
    """Test ChunkStore functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize chunk store."""
        from src.indexation.chunk_store import ChunkStore
        self.store = ChunkStore()
    
    def test_chunk_store_has_chunks(self):
        """Verify that chunks exist in the store."""
        count = self.store.count_chunks()
        assert count > 0, "ChunkStore should have indexed chunks"
    
    def test_chunk_store_has_trump_doc_chunks(self):
        """Verify Trump document has been chunked."""
        chunks = self.store.get_chunks_by_doc_id(TRUMP_DOC_ID)
        
        assert len(chunks) > 0, (
            f"Trump document {TRUMP_DOC_ID[:16]}... should have chunks"
        )
        
        # Should have multiple chunks (document is ~56K chars)
        assert len(chunks) >= 30, (
            f"Expected >= 30 chunks for large document, got {len(chunks)}"
        )
    
    def test_chunks_have_valid_metadata(self):
        """Verify chunk metadata is properly set."""
        chunks = self.store.get_chunks_by_doc_id(TRUMP_DOC_ID)
        
        if not chunks:
            pytest.skip("No chunks for Trump document")
        
        for chunk in chunks[:5]:  # Check first 5
            assert chunk.doc_id == TRUMP_DOC_ID
            assert chunk.chunk_index >= 0
            assert chunk.total_chunks > 0
            assert chunk.chunk_index < chunk.total_chunks
            assert len(chunk.content) > 0
            assert chunk.offset_start >= 0
            assert chunk.offset_end > chunk.offset_start


class TestSearchIntegration:
    """Integration tests for hybrid search with chunks."""
    
    def test_search_chunks_performance(self):
        """Verify chunk search completes in reasonable time."""
        from src.search.hybrid_engine import HybridSearchEngine
        import time
        
        engine = HybridSearchEngine()
        
        start = time.time()
        response = engine.search_chunks("Trump tariff policy", limit=5)
        elapsed_ms = (time.time() - start) * 1000
        
        # Should complete within 10 seconds (includes embedding generation)
        assert elapsed_ms < 10000, (
            f"Chunk search took {elapsed_ms:.0f}ms, expected < 10000ms"
        )
        
        # Response should have timing info
        assert response.search_time_ms > 0
