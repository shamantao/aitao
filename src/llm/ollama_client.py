"""
OllamaClient: Wrapper for Ollama LLM server API.

This module provides a client to interact with Ollama, a local LLM serving system.
It supports model listing, chat completion, text generation, and embeddings.

Ollama provides:
- Multi-model support (hot-swap, automatic loading/unloading)
- OpenAI-compatible API endpoints
- Memory management and GPU optimization
- Standard HTTP interface at http://localhost:11434 (default)

The client handles:
- Connection management and error handling
- Streaming responses (SSE - Server-Sent Events)
- Request/response formatting
- Model availability checking
"""

import json
import logging
from typing import Optional, Dict, Any, List, Iterator
from dataclasses import dataclass
import httpx

from src.core.config import ConfigManager
from src.core.logger import StructuredLogger


@dataclass
class OllamaModel:
    """Represents an available Ollama model."""
    name: str
    size: int  # bytes
    digest: str
    modified_at: str


@dataclass
class OllamaChatMessage:
    """Chat message format."""
    role: str  # "user", "assistant", "system"
    content: str


class OllamaConnectionError(Exception):
    """Raised when Ollama server is unreachable."""
    pass


class OllamaModelNotFound(Exception):
    """Raised when requested model is not available."""
    pass


class OllamaClient:
    """
    Client for interacting with Ollama LLM server.
    
    Features:
    - List available models
    - Chat completion (with streaming support)
    - Text generation
    - Embedding generation
    - Error handling and connection management
    """
    
    def __init__(self, config: ConfigManager, logger: StructuredLogger):
        """
        Initialize OllamaClient.
        
        Args:
            config: ConfigManager instance for reading config.yaml
            logger: StructuredLogger instance for logging operations
        """
        self.config = config
        self.logger = logger
        
        # Get Ollama configuration
        llm_config = config.get_section("llm")
        if not llm_config:
            raise ValueError("Missing 'llm' section in config.yaml")
        
        # Support both nested (ollama.host) and flat (ollama_url) config formats
        ollama_config = llm_config.get("ollama", {})
        self.host = (
            ollama_config.get("host") or 
            llm_config.get("ollama_url") or 
            "http://localhost:11434"
        )
        self.default_model = (
            ollama_config.get("default_model") or 
            llm_config.get("default_model") or 
            "qwen2.5-coder:7b"
        )
        
        # HTTP client with timeout
        self.client = httpx.Client(timeout=60.0, follow_redirects=True)
        self.async_client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        
        self.logger.info(
            "OllamaClient initialized",
            metadata={"host": self.host, "default_model": self.default_model}
        )
    
    def _check_connection(self) -> bool:
        """
        Check if Ollama server is reachable.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.get(f"{self.host}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                "Ollama connection failed",
                metadata={"error": str(e), "host": self.host}
            )
            return False
    
    def list_models(self) -> List[OllamaModel]:
        """
        List all available models on Ollama server.
        
        Returns:
            List of OllamaModel objects
            
        Raises:
            OllamaConnectionError: If server unreachable
        """
        try:
            response = self.client.get(f"{self.host}/api/tags")
            
            if response.status_code != 200:
                raise OllamaConnectionError(
                    f"Ollama returned status {response.status_code}"
                )
            
            data = response.json()
            models = []
            
            for model_data in data.get("models", []):
                model = OllamaModel(
                    name=model_data["name"],
                    size=model_data.get("size", 0),
                    digest=model_data.get("digest", ""),
                    modified_at=model_data.get("modified_at", "")
                )
                models.append(model)
            
            self.logger.info(
                f"Listed {len(models)} models from Ollama",
                metadata={"models": [m.name for m in models]}
            )
            return models
            
        except httpx.ConnectError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.host}") from e
        except Exception as e:
            self.logger.error(
                "Error listing models",
                metadata={"error": str(e)}
            )
            raise
    
    def chat(
        self,
        messages: List[OllamaChatMessage],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> Dict[str, Any] | Iterator[str]:
        """
        Chat completion endpoint (Ollama-compatible format).
        
        Args:
            messages: List of chat messages
            model: Model name (uses default if not specified)
            stream: Whether to stream response
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter
            **kwargs: Additional Ollama parameters
            
        Returns:
            Dict with response (if stream=False) or Iterator (if stream=True)
            
        Raises:
            OllamaConnectionError: If server unreachable
            OllamaModelNotFound: If model not available
        """
        if not model:
            model = self.default_model
        
        # Verify model exists
        available_models = [m.name for m in self.list_models()]
        if model not in available_models:
            raise OllamaModelNotFound(
                f"Model '{model}' not found. Available: {available_models}"
            )
        
        # Format messages for Ollama API
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": stream,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }
        
        try:
            if stream:
                return self._chat_stream(payload)
            else:
                return self._chat_sync(payload)
        except Exception as e:
            self.logger.error(
                "Chat error",
                metadata={"error": str(e), "model": model}
            )
            raise
    
    def _chat_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronous chat request."""
        response = self.client.post(
            f"{self.host}/api/chat",
            json=payload
        )
        
        if response.status_code != 200:
            raise OllamaConnectionError(
                f"Chat request failed with status {response.status_code}"
            )
        
        return response.json()
    
    def _chat_stream(self, payload: Dict[str, Any]) -> Iterator[str]:
        """Execute streaming chat request (returns JSON lines as strings)."""
        with self.client.stream(
            "POST",
            f"{self.host}/api/chat",
            json=payload
        ) as response:
            if response.status_code != 200:
                raise OllamaConnectionError(
                    f"Chat stream failed with status {response.status_code}"
                )
            
            for line in response.iter_lines():
                if line.strip():
                    # Yield raw JSON line for caller to parse
                    yield line
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | Iterator[str]:
        """
        Text generation endpoint (non-chat mode).
        
        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            stream: Whether to stream response
            **kwargs: Additional Ollama parameters
            
        Returns:
            Dict with response (if stream=False) or Iterator (if stream=True)
        """
        if not model:
            model = self.default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        try:
            if stream:
                return self._generate_stream(payload)
            else:
                return self._generate_sync(payload)
        except Exception as e:
            self.logger.error(
                "Generate error",
                metadata={"error": str(e), "model": model}
            )
            raise
    
    def _generate_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronous generate request."""
        try:
            response = self.client.post(
                f"{self.host}/api/generate",
                json=payload
            )
        except httpx.ConnectError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}") from e
        
        if response.status_code != 200:
            raise OllamaConnectionError(
                f"Generate request failed with status {response.status_code}"
            )
        
        return response.json()
    
    def _generate_stream(self, payload: Dict[str, Any]) -> Iterator[str]:
        """Execute streaming generate request."""
        with self.client.stream(
            "POST",
            f"{self.host}/api/generate",
            json=payload
        ) as response:
            if response.status_code != 200:
                raise OllamaConnectionError(
                    f"Generate stream failed with status {response.status_code}"
                )
            
            for line in response.iter_text():
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        self.logger.debug(f"Skipping malformed JSON: {line}")
    
    def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Input text
            model: Model name (uses default if not specified)
            
        Returns:
            List of embedding values (vector)
        """
        if not model:
            model = self.default_model
        
        payload = {
            "model": model,
            "prompt": text
        }
        
        try:
            response = self.client.post(
                f"{self.host}/api/embeddings",
                json=payload
            )
            
            if response.status_code != 200:
                raise OllamaConnectionError(
                    f"Embeddings request failed with status {response.status_code}"
                )
            
            data = response.json()
            return data.get("embedding", [])
            
        except Exception as e:
            self.logger.error(
                "Embeddings error",
                metadata={"error": str(e), "model": model}
            )
            raise
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get detailed info about a model.
        
        Args:
            model: Model name
            
        Returns:
            Dict with model details (size, parameters, format, etc.)
        """
        payload = {"name": model}
        
        try:
            response = self.client.post(
                f"{self.host}/api/show",
                json=payload
            )
            
            if response.status_code != 200:
                raise OllamaModelNotFound(f"Model '{model}' not found")
            
            return response.json()
            
        except Exception as e:
            self.logger.error(
                "Model info error",
                metadata={"error": str(e), "model": model}
            )
            raise
    
    def delete_model(self, model: str) -> bool:
        """
        Delete a model from Ollama.
        
        Uses DELETE /api/delete endpoint to remove model files.
        This frees up disk space but doesn't remove from config.yaml.
        
        Args:
            model: Model name to delete (e.g., "llama3.1:8b")
        
        Returns:
            True if successful
        
        Raises:
            OllamaConnectionError: If server is unreachable
            Exception: If deletion fails
        """
        if not self._check_connection():
            raise OllamaConnectionError(
                f"Cannot delete model: Ollama not reachable at {self.host}"
            )
        
        try:
            response = self.client.delete(
                f"{self.host}/api/delete",
                json={"name": model}
            )
            response.raise_for_status()
            self.logger.info(
                "Model deleted from Ollama",
                metadata={"model": model}
            )
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.warning(
                    "Model not found in Ollama",
                    metadata={"model": model}
                )
                return False
            raise
        except Exception as e:
            self.logger.error(
                "Model deletion error",
                metadata={"error": str(e), "model": model}
            )
            raise

    def is_healthy(self) -> bool:
        """
        Check if Ollama server is healthy.
        
        Returns:
            True if server is responsive, False otherwise
        """
        return self._check_connection()
    
    def close(self):
        """Close HTTP client connections."""
        self.client.close()
    
    async def aclose(self):
        """Close async HTTP client connections."""
        await self.async_client.aclose()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
