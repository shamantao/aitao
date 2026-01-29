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

__all__ = [
    "OllamaClient",
    "OllamaModel",
    "OllamaChatMessage",
    "OllamaConnectionError",
    "OllamaModelNotFound",
]
