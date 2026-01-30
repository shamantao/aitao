"""
LLM module: Language Model Management and RAG integration.

This module provides:
- OllamaClient: Interface to Ollama local LLM server
- RAGEngine: Retrieval-Augmented Generation engine
- ModelManager: LLM model lifecycle management (US-021b)
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

from .model_manager import (
    ModelManager,
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
    # Model Manager
    "ModelManager",
]
