"""
LLM module: Language Model Management and RAG integration.

This module provides:
- OllamaClient: Interface to Ollama local LLM server
- RAGEngine: Retrieval-Augmented Generation engine
- Chat integration with document context enrichment
"""

from .ollama_client import (
    OllamaClient,
    OllamaModel,
    OllamaChatMessage,
    OllamaConnectionError,
    OllamaModelNotFound,
)

from .rag_engine import (
    RAGEngine,
    RAGResult,
    ContextDocument,
)

__all__ = [
    # Ollama Client
    "OllamaClient",
    "OllamaModel",
    "OllamaChatMessage",
    "OllamaConnectionError",
    "OllamaModelNotFound",
    # RAG Engine
    "RAGEngine",
    "RAGResult",
    "ContextDocument",
]
