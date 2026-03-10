"""
LLM module: Language Model Management and RAG integration.

This module provides:
- OllamaClient: Interface to Ollama local LLM server
- RAGEngine: Retrieval-Augmented Generation engine
- ModelManager: LLM model lifecycle management (US-021b)
- BackendRouter: Unified LLM routing (MLX/Ollama) (US-032)
- MLXBackend: Apple Silicon accelerated inference (US-031)
- Protocols: Standard interfaces for backends
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

from .protocols import (
    LLMBackendProtocol,
    EmbeddingBackendProtocol,
    ChatMessage,
    GenerationResult,
)

from .backend_router import (
    BackendRouter,
    OllamaBackendAdapter,
)

# Conditional MLX import (only on Apple Silicon)
try:
    from .mlx_backend import MLXBackend
    _MLX_AVAILABLE = True
except ImportError:
    MLXBackend = None  # type: ignore
    _MLX_AVAILABLE = False

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
    # Backend Router (US-032)
    "BackendRouter",
    "OllamaBackendAdapter",
    # Protocols
    "LLMBackendProtocol",
    "EmbeddingBackendProtocol",
    "ChatMessage",
    "GenerationResult",
    # MLX Backend (optional)
    "MLXBackend",
]
