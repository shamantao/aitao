"""
Unit tests for US-042 — IntentRouter + FactualQueryHandler.

Tests 10 prompts covering the 3 intent categories.
"""

import pytest
from src.llm.intent_router import IntentRouter
from src.llm.factual_query import extract_path_from_prompt


class TestIntentRouter:
    """Tests for IntentRouter.classify()."""

    def setup_method(self):
        self.router = IntentRouter()

    # --- Factual intents ---
    def test_combien_factual(self):
        assert self.router.classify("combien de livres dans ~/MEGA/EBOOK/Contes ?") == "factual"

    def test_liste_moi_factual(self):
        assert self.router.classify("liste-moi les fichiers PDF de ~/Documents/") == "factual"

    def test_how_many_factual(self):
        assert self.router.classify("how many files do you have in /Users/phil/Desktop?") == "factual"

    def test_quels_fichiers_factual(self):
        assert self.router.classify("quels fichiers sont indexés dans ~/Downloads ?") == "factual"

    def test_est_ce_que_tu_as_factual(self):
        assert self.router.classify("est-ce que tu as des documents en chinois ?") == "factual"

    # --- Summarize intents ---
    def test_resume_moi_summarize(self):
        assert self.router.classify("résume-moi Ergonomie des interfaces - Dunod.pdf") == "summarize"

    def test_fais_resume_summarize(self):
        assert self.router.classify("fais-moi un résumé complet de ce livre") == "summarize"

    def test_summarize_english(self):
        assert self.router.classify("summarize the entire report_2025.pdf") == "summarize"

    # --- RAG (default) intents ---
    def test_rag_explain(self):
        assert self.router.classify("explique-moi le fonctionnement de l'OCR dans AiTao") == "rag"

    def test_rag_empty_prompt(self):
        assert self.router.classify("") == "rag"

    def test_rag_generic_question(self):
        assert self.router.classify("Que dit ce document sur les délais ?") == "rag"


class TestExtractPathFromPrompt:
    """Tests for extract_path_from_prompt helper."""

    def test_home_tilde(self):
        path = extract_path_from_prompt("combien de fichiers dans ~/MEGA/EBOOK/Contes ?")
        assert path is not None
        assert "MEGA/EBOOK/Contes" in path

    def test_absolute_unix(self):
        path = extract_path_from_prompt("liste /Users/phil/Documents")
        assert path is not None
        assert "/Users/phil/Documents" in path

    def test_no_path(self):
        path = extract_path_from_prompt("explique-moi l'architecture")
        assert path is None
