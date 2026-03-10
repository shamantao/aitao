"""
Backend Router for LLM Request Routing.

This module provides intelligent routing of LLM requests to the appropriate backend
(MLX on Apple Silicon, Ollama elsewhere) based on platform capabilities and configuration.

Architecture:
    BackendRouter acts as a facade over multiple backends, selecting the best one
    based on availability and user configuration. It implements LLMBackendProtocol
    so callers don't need to know which backend is active.

Fallback Chain:
    1. MLX (if available and enabled) - Fastest on Apple Silicon
    2. Ollama (universal fallback) - Works everywhere

Usage:
    router = BackendRouter(config, logger)
    result = router.generate("Hello world", model="qwen2.5-coder:7b")
    # Automatically routes to MLX or Ollama
"""

import logging
from typing import Any, Dict, Iterator, List, Optional

from src.core.config import ConfigManager
from src.core.logger import StructuredLogger
from src.core.platform import get_platform_info, PlatformInfo
from src.llm.protocols import (
    ChatMessage,
    GenerationResult,
    LLMBackendProtocol,
)


# ============================================================================
# Backend Wrapper for Ollama
# ============================================================================

class OllamaBackendAdapter:
    """
    Adapter wrapping OllamaClient to implement LLMBackendProtocol.
    
    This adapter converts OllamaClient's API to the standard protocol,
    enabling it to be used interchangeably with MLXBackend.
    """
    
    def __init__(self, config: ConfigManager, logger: StructuredLogger):
        """Initialize the Ollama adapter."""
        # Import here to avoid circular dependency
        from src.llm.ollama_client import OllamaClient, OllamaChatMessage
        
        self._config = config
        self._logger = logger
        self._client: Optional[OllamaClient] = None
        self._available: Optional[bool] = None
        
        # Store reference to message class
        self._ChatMessage = OllamaChatMessage
    
    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "ollama"
    
    def _ensure_client(self) -> None:
        """Lazy initialization of OllamaClient."""
        if self._client is None:
            from src.llm.ollama_client import OllamaClient
            self._client = OllamaClient(self._config, self._logger)
    
    def is_available(self) -> bool:
        """Check if Ollama is available and responding."""
        if self._available is not None:
            return self._available
        
        try:
            self._ensure_client()
            assert self._client is not None
            self._available = self._client._check_connection()
        except Exception:
            self._available = False
        
        return self._available
    
    def list_models(self) -> List[str]:
        """List available Ollama models."""
        self._ensure_client()
        assert self._client is not None
        
        models = self._client.list_models()
        return [m.name for m in models]
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate text using Ollama."""
        import time
        
        self._ensure_client()
        assert self._client is not None
        
        start_time = time.time()
        
        response = self._client.generate(
            prompt=prompt,
            model=model,
            stream=False,
            num_predict=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        text = response.get("response", "")
        
        # Ollama returns token counts in response
        tokens = response.get("eval_count", len(text.split()))
        tps = (tokens / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0
        
        return GenerationResult(
            text=text,
            model=model or self._client.default_model,
            backend="ollama",
            tokens_generated=tokens,
            generation_time_ms=elapsed_ms,
            tokens_per_second=tps,
        )
    
    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """Chat completion using Ollama."""
        import time
        
        self._ensure_client()
        assert self._client is not None
        
        # Convert to OllamaChatMessage format
        ollama_messages = [
            self._ChatMessage(role=msg.role, content=msg.content)
            for msg in messages
        ]
        
        start_time = time.time()
        
        response = self._client.chat(
            messages=ollama_messages,
            model=model,
            stream=False,
            temperature=temperature,
            num_predict=max_tokens,
            **kwargs,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Extract response text
        message = response.get("message", {})
        text = message.get("content", "")
        
        # Token counts
        tokens = response.get("eval_count", len(text.split()))
        tps = (tokens / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0
        
        return GenerationResult(
            text=text,
            model=model or self._client.default_model,
            backend="ollama",
            tokens_generated=tokens,
            generation_time_ms=elapsed_ms,
            tokens_per_second=tps,
        )
    
    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream generation using Ollama."""
        self._ensure_client()
        assert self._client is not None
        
        stream = self._client.generate(
            prompt=prompt,
            model=model,
            stream=True,
            num_predict=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        
        # Ollama stream already yields text chunks
        yield from stream


# ============================================================================
# Backend Router
# ============================================================================

class BackendRouter:
    """
    Unified LLM backend router with automatic fallback.
    
    This class provides a single interface for LLM operations, automatically
    selecting the best available backend based on platform and configuration.
    
    Backend Selection Logic:
        1. Read config.llm.backend setting (auto/mlx/ollama)
        2. If "auto": detect platform and use MLX on Apple Silicon
        3. Verify backend availability before use
        4. Fallback to Ollama if primary unavailable
    
    Attributes:
        active_backend: The currently selected backend instance.
        backend_name: Name of the active backend ("mlx" or "ollama").
    """
    
    def __init__(self, config: ConfigManager, logger: StructuredLogger):
        """
        Initialize the backend router.
        
        Args:
            config: Configuration manager instance.
            logger: Structured logger for operation logging.
        """
        self._config = config
        self._logger = logger
        self._platform: PlatformInfo = get_platform_info()
        
        # Backend instances (lazy loaded)
        self._mlx_backend: Optional[LLMBackendProtocol] = None
        self._ollama_backend: Optional[OllamaBackendAdapter] = None
        self._active_backend: Optional[LLMBackendProtocol] = None
        
        # Read configuration
        llm_config = config.get_section("llm") or {}
        self._backend_preference = llm_config.get("backend", "auto")
        self._mlx_enabled = llm_config.get("mlx", {}).get("enabled", True)
        
        self._logger.info(
            "BackendRouter initializing",
            metadata={
                "backend_preference": self._backend_preference,
                "mlx_enabled": self._mlx_enabled,
                "platform": self._platform.os,
                "arch": self._platform.arch,
                "has_mlx": self._platform.has_mlx,
            }
        )
        
        # Initialize backends
        self._initialize_backends()
    
    def _initialize_backends(self) -> None:
        """Initialize and select the appropriate backend."""
        # Always create Ollama adapter (universal fallback)
        self._ollama_backend = OllamaBackendAdapter(self._config, self._logger)
        
        # Try to create MLX backend if conditions are met
        if self._should_try_mlx():
            try:
                from src.llm.mlx_backend import MLXBackend
                self._mlx_backend = MLXBackend(self._config, self._logger)
                self._logger.info("MLX backend initialized successfully")
            except ImportError as e:
                self._logger.warning(
                    "MLX backend unavailable (import error)",
                    metadata={"error": str(e)}
                )
                self._mlx_backend = None
            except Exception as e:
                self._logger.warning(
                    "MLX backend initialization failed",
                    metadata={"error": str(e)}
                )
                self._mlx_backend = None
        
        # Select active backend based on preference
        self._select_backend()
    
    def _should_try_mlx(self) -> bool:
        """Determine if we should attempt to load MLX backend."""
        # Disabled by config
        if not self._mlx_enabled:
            return False
        
        # Explicit Ollama preference
        if self._backend_preference == "ollama":
            return False
        
        # Platform must support MLX
        if not self._platform.is_apple_silicon:
            return False
        
        return True
    
    def _select_backend(self) -> None:
        """Select the active backend based on preference and availability."""
        # Explicit MLX preference
        if self._backend_preference == "mlx":
            if self._mlx_backend and self._mlx_backend.is_available():
                self._active_backend = self._mlx_backend
                self._logger.info("Using MLX backend (explicit preference)")
                return
            self._logger.warning("MLX requested but unavailable, falling back to Ollama")
        
        # Explicit Ollama preference
        elif self._backend_preference == "ollama":
            if self._ollama_backend and self._ollama_backend.is_available():
                self._active_backend = self._ollama_backend
                self._logger.info("Using Ollama backend (explicit preference)")
                return
            raise RuntimeError("Ollama backend requested but unavailable")
        
        # Auto mode: prefer MLX on Apple Silicon
        else:  # auto
            if self._mlx_backend and self._mlx_backend.is_available():
                self._active_backend = self._mlx_backend
                self._logger.info("Using MLX backend (auto-detected Apple Silicon)")
                return
        
        # Fallback to Ollama
        if self._ollama_backend and self._ollama_backend.is_available():
            self._active_backend = self._ollama_backend
            self._logger.info("Using Ollama backend (fallback)")
            return
        
        raise RuntimeError("No LLM backend available. Start Ollama or install MLX.")
    
    # ========================================================================
    # Public API (implements LLMBackendProtocol interface)
    # ========================================================================
    
    @property
    def backend_name(self) -> str:
        """Return the name of the active backend."""
        if self._active_backend:
            return self._active_backend.backend_name
        return "none"
    
    @property
    def active_backend(self) -> Optional[LLMBackendProtocol]:
        """Return the active backend instance."""
        return self._active_backend
    
    def is_available(self) -> bool:
        """Check if any backend is available."""
        return self._active_backend is not None
    
    def list_models(self) -> List[str]:
        """List models from the active backend."""
        if not self._active_backend:
            return []
        return self._active_backend.list_models()
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """
        Generate text using the active backend.
        
        Args:
            prompt: Input prompt for generation.
            model: Model to use (uses backend default if None).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            **kwargs: Additional backend-specific parameters.
            
        Returns:
            GenerationResult with text and metadata.
            
        Raises:
            RuntimeError: If no backend is available.
        """
        if not self._active_backend:
            raise RuntimeError("No LLM backend available")
        
        self._logger.debug(
            "Routing generate request",
            metadata={
                "backend": self.backend_name,
                "model": model,
                "prompt_length": len(prompt),
            }
        )
        
        result = self._active_backend.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        
        self._logger.info(
            "Generation completed",
            metadata=result.to_dict()
        )
        
        return result
    
    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """
        Chat completion using the active backend.
        
        Args:
            messages: Conversation history as ChatMessage list.
            model: Model to use.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            **kwargs: Additional parameters.
            
        Returns:
            GenerationResult with assistant response.
        """
        if not self._active_backend:
            raise RuntimeError("No LLM backend available")
        
        self._logger.debug(
            "Routing chat request",
            metadata={
                "backend": self.backend_name,
                "model": model,
                "message_count": len(messages),
            }
        )
        
        result = self._active_backend.chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        
        self._logger.info(
            "Chat completed",
            metadata=result.to_dict()
        )
        
        return result
    
    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        Stream generation using the active backend.
        
        Args:
            prompt: Input prompt.
            model: Model to use.
            max_tokens: Maximum tokens.
            temperature: Sampling temperature.
            **kwargs: Additional parameters.
            
        Yields:
            Generated text chunks.
        """
        if not self._active_backend:
            raise RuntimeError("No LLM backend available")
        
        self._logger.debug(
            "Routing stream request",
            metadata={
                "backend": self.backend_name,
                "model": model,
            }
        )
        
        yield from self._active_backend.generate_stream(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
    
    # ========================================================================
    # Backend Management
    # ========================================================================
    
    def switch_backend(self, backend_name: str) -> bool:
        """
        Manually switch to a specific backend.
        
        Args:
            backend_name: "mlx" or "ollama"
            
        Returns:
            True if switch successful, False otherwise.
        """
        if backend_name == "mlx":
            if self._mlx_backend and self._mlx_backend.is_available():
                self._active_backend = self._mlx_backend
                self._logger.info("Switched to MLX backend")
                return True
            self._logger.warning("Cannot switch to MLX: unavailable")
            return False
        
        elif backend_name == "ollama":
            if self._ollama_backend and self._ollama_backend.is_available():
                self._active_backend = self._ollama_backend
                self._logger.info("Switched to Ollama backend")
                return True
            self._logger.warning("Cannot switch to Ollama: unavailable")
            return False
        
        self._logger.error(f"Unknown backend: {backend_name}")
        return False
    
    def get_backends_status(self) -> Dict[str, Any]:
        """
        Get status of all backends.
        
        Returns:
            Dict with backend availability and active status.
        """
        status = {
            "active": self.backend_name,
            "platform": {
                "os": self._platform.os,
                "arch": self._platform.arch,
                "is_apple_silicon": self._platform.is_apple_silicon,
                "has_mlx": self._platform.has_mlx,
            },
            "backends": {},
        }
        
        # MLX status
        if self._mlx_backend:
            status["backends"]["mlx"] = {
                "available": self._mlx_backend.is_available(),
                "active": self._active_backend == self._mlx_backend,
            }
        else:
            status["backends"]["mlx"] = {
                "available": False,
                "active": False,
                "reason": "Not initialized (platform unsupported or disabled)",
            }
        
        # Ollama status
        if self._ollama_backend:
            status["backends"]["ollama"] = {
                "available": self._ollama_backend.is_available(),
                "active": self._active_backend == self._ollama_backend,
            }
        else:
            status["backends"]["ollama"] = {
                "available": False,
                "active": False,
            }
        
        return status
