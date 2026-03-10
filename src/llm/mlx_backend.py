"""
MLX Backend for AiTao LLM Inference.

This module provides MLX-accelerated LLM inference on Apple Silicon Macs.
MLX is Apple's machine learning framework optimized for M1/M2/M3/M4 chips,
providing 2-3x faster inference compared to CPU-based solutions.

Features:
- Native Apple Silicon optimization via Metal
- Unified memory architecture (no CPU-GPU transfers)
- Support for quantized models (Q4, Q8, F16)
- Compatible with HuggingFace models via mlx-lm

Requirements:
- macOS on Apple Silicon (M1/M2/M3/M4)
- MLX and mlx-lm packages installed
- Models downloaded from HuggingFace (mlx-community)

Usage:
    from src.llm.mlx_backend import MLXBackend
    
    backend = MLXBackend()
    if backend.is_available():
        result = backend.generate("Hello, world!", model="mlx-community/qwen2.5-coder-7b-4bit")
        print(result.text)

Conformity:
- NFR-001: Platform Support (macOS Apple Silicon priority)
- NFR-005: Maintainability (<400 lines)
"""

import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from src.core.logger import get_logger
from src.core.platform import get_platform_info
from src.llm.protocols import (
    ChatMessage,
    GenerationResult,
    LLMBackendProtocol,
)

logger = get_logger("llm.mlx_backend")


# ============================================================================
# MLX Backend Implementation
# ============================================================================

class MLXBackend:
    """
    MLX-accelerated LLM backend for Apple Silicon.
    
    Implements LLMBackendProtocol for compatibility with BackendRouter.
    Falls back gracefully if MLX is not available.
    """
    
    def __init__(
        self,
        default_model: str = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        cache_dir: Optional[Path] = None,
        quantization: str = "4bit",
    ):
        """
        Initialize MLX backend.
        
        Args:
            default_model: Default HuggingFace model ID for mlx-lm.
            cache_dir: Directory to cache downloaded models.
            quantization: Default quantization level (4bit, 8bit, fp16).
        """
        self._default_model = default_model
        self._cache_dir = cache_dir
        self._quantization = quantization
        self._model_cache: Dict[str, Any] = {}  # {model_id: (model, tokenizer)}
        self._mlx_available: Optional[bool] = None
        
        logger.info(
            "MLXBackend initialized",
            metadata={
                "default_model": default_model,
                "quantization": quantization,
            }
        )
    
    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "mlx"
    
    def is_available(self) -> bool:
        """
        Check if MLX backend is available on this platform.
        
        Returns True only on Apple Silicon with MLX installed.
        """
        if self._mlx_available is not None:
            return self._mlx_available
        
        platform_info = get_platform_info()
        
        if not platform_info.supports_mlx_acceleration():
            logger.debug(
                "MLX not available",
                metadata={"reason": "Platform does not support MLX acceleration"}
            )
            self._mlx_available = False
            return False
        
        # Try importing mlx_lm
        try:
            import mlx_lm
            self._mlx_available = True
            logger.info("MLX backend available", metadata={"mlx_lm_loaded": True})
            return True
        except ImportError as e:
            logger.warning(f"mlx_lm not installed: {e}")
            self._mlx_available = False
            return False
    
    def _load_model(self, model_id: str) -> tuple:
        """
        Load a model with mlx-lm.
        
        Args:
            model_id: HuggingFace model ID or local path.
            
        Returns:
            Tuple of (model, tokenizer).
        """
        if model_id in self._model_cache:
            logger.debug(f"Using cached model: {model_id}")
            return self._model_cache[model_id]
        
        logger.info(f"Loading MLX model: {model_id}")
        start_time = time.time()
        
        try:
            from mlx_lm import load
            
            model, tokenizer = load(model_id)
            
            load_time = time.time() - start_time
            logger.info(
                "MLX model loaded",
                metadata={
                    "model": model_id,
                    "load_time_s": round(load_time, 2),
                }
            )
            
            self._model_cache[model_id] = (model, tokenizer)
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Failed to load MLX model {model_id}: {e}")
            raise
    
    def list_models(self) -> List[str]:
        """
        List available MLX models.
        
        Returns cached models and suggests popular mlx-community models.
        """
        # Cached models
        cached = list(self._model_cache.keys())
        
        # Popular MLX models (suggestions)
        suggested = [
            "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
            "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
            "mlx-community/Llama-3.1-8B-Instruct-4bit",
            "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
        ]
        
        # Return unique list
        return list(set(cached + suggested))
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """
        Generate text from a prompt using MLX.
        
        Args:
            prompt: Input prompt.
            model: Model ID (uses default if None).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            **kwargs: Additional mlx_lm.generate parameters.
            
        Returns:
            GenerationResult with generated text.
        """
        if not self.is_available():
            raise RuntimeError("MLX backend is not available on this platform")
        
        model_id = model or self._default_model
        
        logger.debug(
            "MLX generate request",
            metadata={
                "model": model_id,
                "prompt_length": len(prompt),
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        
        try:
            from mlx_lm import generate as mlx_generate
            
            mlx_model, tokenizer = self._load_model(model_id)
            
            start_time = time.time()
            
            # Generate with mlx_lm
            response = mlx_generate(
                model=mlx_model,
                tokenizer=tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False,
            )
            
            generation_time_ms = (time.time() - start_time) * 1000
            
            # Estimate tokens (rough approximation)
            tokens_generated = len(response.split()) * 1.3  # ~1.3 tokens per word
            tokens_per_second = (tokens_generated / generation_time_ms) * 1000 if generation_time_ms > 0 else 0
            
            result = GenerationResult(
                text=response,
                model=model_id,
                backend="mlx",
                tokens_generated=int(tokens_generated),
                generation_time_ms=generation_time_ms,
                tokens_per_second=tokens_per_second,
            )
            
            logger.info(
                "MLX generation complete",
                metadata=result.to_dict(),
            )
            
            return result
            
        except Exception as e:
            logger.error(f"MLX generation failed: {e}")
            raise
    
    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """
        Generate chat completion from messages.
        
        Converts messages to ChatML format for Qwen models or
        appropriate format for other models.
        
        Args:
            messages: Conversation history.
            model: Model ID.
            max_tokens: Maximum tokens.
            temperature: Sampling temperature.
            **kwargs: Additional parameters.
            
        Returns:
            GenerationResult with assistant's response.
        """
        if not self.is_available():
            raise RuntimeError("MLX backend is not available on this platform")
        
        model_id = model or self._default_model
        
        # Load model and tokenizer to use chat template
        mlx_model, tokenizer = self._load_model(model_id)
        
        # Convert messages to format expected by tokenizer
        messages_dict = [msg.to_dict() for msg in messages]
        
        try:
            # Use tokenizer's chat template if available
            if hasattr(tokenizer, 'apply_chat_template'):
                prompt = tokenizer.apply_chat_template(
                    messages_dict,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            else:
                # Fallback to ChatML format (for Qwen models)
                prompt = self._format_chatml(messages)
            
            return self.generate(
                prompt=prompt,
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            
        except Exception as e:
            logger.error(f"MLX chat failed: {e}")
            raise
    
    def _format_chatml(self, messages: List[ChatMessage]) -> str:
        """
        Format messages in ChatML format (for Qwen models).
        
        ChatML format:
        <|im_start|>system
        {system_prompt}<|im_end|>
        <|im_start|>user
        {user_message}<|im_end|>
        <|im_start|>assistant
        """
        parts = []
        for msg in messages:
            parts.append(f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>")
        
        # Add generation prompt
        parts.append("<|im_start|>assistant\n")
        
        return "\n".join(parts)
    
    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        Stream generation token by token.
        
        MLX supports streaming via mlx_lm.stream_generate.
        
        Yields:
            Generated text chunks.
        """
        if not self.is_available():
            raise RuntimeError("MLX backend is not available on this platform")
        
        model_id = model or self._default_model
        
        try:
            from mlx_lm import stream_generate
            
            mlx_model, tokenizer = self._load_model(model_id)
            
            # Stream tokens
            for token in stream_generate(
                model=mlx_model,
                tokenizer=tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                temp=temperature,
            ):
                yield token
                
        except ImportError:
            # Fallback to non-streaming if stream_generate not available
            logger.warning("stream_generate not available, using non-streaming")
            result = self.generate(prompt, model, max_tokens, temperature, **kwargs)
            yield result.text
        except Exception as e:
            logger.error(f"MLX streaming failed: {e}")
            raise
    
    def unload_model(self, model_id: Optional[str] = None) -> None:
        """
        Unload model from cache to free memory.
        
        Args:
            model_id: Specific model to unload, or all if None.
        """
        if model_id:
            if model_id in self._model_cache:
                del self._model_cache[model_id]
                logger.info(f"Unloaded MLX model: {model_id}")
        else:
            self._model_cache.clear()
            logger.info("Unloaded all MLX models")


# ============================================================================
# Module-level Factory
# ============================================================================

_mlx_backend: Optional[MLXBackend] = None


def get_mlx_backend(
    default_model: str = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    **kwargs: Any,
) -> MLXBackend:
    """
    Get or create the MLX backend singleton.
    
    Args:
        default_model: Default model to use.
        **kwargs: Additional MLXBackend parameters.
        
    Returns:
        MLXBackend instance.
    """
    global _mlx_backend
    
    if _mlx_backend is None:
        _mlx_backend = MLXBackend(default_model=default_model, **kwargs)
    
    return _mlx_backend


def reset_mlx_backend() -> None:
    """Reset the MLX backend singleton (for testing)."""
    global _mlx_backend
    if _mlx_backend:
        _mlx_backend.unload_model()
    _mlx_backend = None
