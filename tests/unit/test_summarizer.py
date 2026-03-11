"""
Unit tests for US-043 — MapReduceSummarizer.

Tests helper functions that don't require live services.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.llm.summarizer import (
    MapReduceSummarizer,
    _extract_doc_name_from_prompt,
    _GROUP_SIZE,
    _MAX_CHUNKS,
)


class TestExtractDocNameFromPrompt:
    """Tests for _extract_doc_name_from_prompt helper."""

    def test_extracts_pdf_filename(self):
        name = _extract_doc_name_from_prompt("résume-moi Ergonomie des interfaces - Dunod.pdf")
        assert name is not None
        assert "Dunod.pdf" in name or "Ergonomie" in name

    def test_extracts_quoted_title(self):
        name = _extract_doc_name_from_prompt('résume-moi "Mon rapport annuel"')
        assert name == "Mon rapport annuel"

    def test_extracts_docx(self):
        name = _extract_doc_name_from_prompt("summarize report_2025.docx please")
        assert name is not None
        assert "report_2025.docx" in name

    def test_no_name_returns_none(self):
        name = _extract_doc_name_from_prompt("explique-moi le RAG")
        assert name is None


class TestMapReduceSummarizer:
    """Tests for MapReduceSummarizer without live LLM/DB."""

    def _make_chunk(self, idx: int, content: str = "chunk content"):
        """Create a minimal mock Chunk object."""
        c = MagicMock()
        c.chunk_index = idx
        c.content = content
        return c

    def test_representative_sample_below_cap(self):
        summarizer = MapReduceSummarizer()
        chunks = [self._make_chunk(i) for i in range(50)]
        result = summarizer._representative_sample(chunks, n=100)
        assert result == chunks  # No sampling needed

    def test_representative_sample_above_cap(self):
        summarizer = MapReduceSummarizer()
        chunks = [self._make_chunk(i) for i in range(200)]
        result = summarizer._representative_sample(chunks, n=50)
        assert len(result) == 50
        # First and last chunks should be represented
        assert result[0].chunk_index == 0

    def test_no_doc_name_yields_error(self):
        summarizer = MapReduceSummarizer()
        llm_fn = MagicMock(return_value="summary")
        parts = list(summarizer.summarize_prompt("explique le RAG", llm_fn))
        assert len(parts) == 1
        assert "could not identify" in parts[0].lower() or "cannot" in parts[0].lower()

    def test_doc_not_found_yields_error(self):
        summarizer = MapReduceSummarizer()
        # Mock the meilisearch search to return empty
        with patch.object(summarizer, "_find_doc_id", return_value=None):
            llm_fn = MagicMock(return_value="summary")
            parts = list(summarizer.summarize_prompt(
                'résume-moi "MonDocument.pdf"', llm_fn
            ))
        assert any("no document matching" in p.lower() or "introuvable" in p.lower() for p in parts)

    def test_full_pipeline_with_mocks(self):
        """Integration test of Map-Reduce pipeline with 3 chunks."""
        summarizer = MapReduceSummarizer()
        chunks = [self._make_chunk(i, f"Content of section {i}") for i in range(3)]

        with (
            patch.object(summarizer, "_find_doc_id", return_value="abc123"),
            patch.object(summarizer.chunk_store, "get_chunks_by_doc_id", return_value=chunks),
        ):
            llm_fn = MagicMock(return_value="A brief summary of this section.")
            parts = list(summarizer.summarize_prompt(
                'résume-moi "Test Doc.pdf"', llm_fn, group_size=2
            ))

        # Should yield: searching, found chunks, starting, map parts, reduce
        text = "\n".join(parts)
        assert "Test Doc.pdf" in text
        assert "Final summary" in text or "synthesis" in text.lower()
