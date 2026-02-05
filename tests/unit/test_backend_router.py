"""
Unit tests for Backend Router (US-032).

Tests the BackendRouter class which provides unified routing
between MLX and Ollama backends based on platform capabilities.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List, Iterator, Any, Optional

from src.llm.backend_router import BackendRouter, OllamaBackendAdapter
from src.llm.protocols import ChatMessage, GenerationResult


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock ConfigManager."""
    config = MagicMock()
    config.get_section.return_value = {
        "backend": "auto",
        "ollama": {
            "host": "http://localhost:11434",
            "default_model": "qwen2.5-coder:7b"
        },
        "mlx": {
            "enabled": True,
            "default_model": "mlx-community/Qwen2.5-Coder-7B-4bit",
            "quantization": "q4",
        }
    }
    return config


@pytest.fixture
def mock_logger():
    """Create a mock StructuredLogger."""
    logger = MagicMock()
    return logger


@pytest.fixture
def mock_platform_apple_silicon():
    """Mock platform info for Apple Silicon Mac."""
    platform = MagicMock()
    platform.os = "macOS"
    platform.arch = "arm64"
    platform.is_apple_silicon = True
    platform.has_mlx = True
    platform.has_metal = True
    platform.cpu_cores = 10
    platform.memory_gb = 64.0
    return platform


@pytest.fixture
def mock_platform_linux():
    """Mock platform info for Linux x86_64."""
    platform = MagicMock()
    platform.os = "Linux"
    platform.arch = "x86_64"
    platform.is_apple_silicon = False
    platform.has_mlx = False
    platform.has_metal = False
    platform.cpu_cores = 8
    platform.memory_gb = 32.0
    return platform


# ============================================================================
# OllamaBackendAdapter Tests
# ============================================================================

class TestOllamaBackendAdapter:
    """Tests for the OllamaBackendAdapter class."""
    
    def test_backend_name(self, mock_config, mock_logger):
        """Test backend name property."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        assert adapter.backend_name == "ollama"
    
    @patch("src.llm.backend_router.OllamaBackendAdapter._ensure_client")
    def test_is_available_true(self, mock_ensure, mock_config, mock_logger):
        """Test availability check when Ollama is running."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        adapter._client = MagicMock()
        adapter._client._check_connection.return_value = True
        
        assert adapter.is_available() is True
    
    @patch("src.llm.backend_router.OllamaBackendAdapter._ensure_client")
    def test_is_available_false(self, mock_ensure, mock_config, mock_logger):
        """Test availability check when Ollama is not running."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        adapter._client = MagicMock()
        adapter._client._check_connection.return_value = False
        
        assert adapter.is_available() is False
    
    @patch("src.llm.backend_router.OllamaBackendAdapter._ensure_client")
    def test_is_available_cached(self, mock_ensure, mock_config, mock_logger):
        """Test that availability is cached."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        adapter._available = True
        
        # Should return cached value without checking
        assert adapter.is_available() is True
        mock_ensure.assert_not_called()
    
    @patch("src.llm.backend_router.OllamaBackendAdapter._ensure_client")
    def test_list_models(self, mock_ensure, mock_config, mock_logger):
        """Test listing models from Ollama."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        
        # Mock the client and models
        mock_model1 = MagicMock()
        mock_model1.name = "qwen2.5-coder:7b"
        mock_model2 = MagicMock()
        mock_model2.name = "llama3.1:8b"
        
        adapter._client = MagicMock()
        adapter._client.list_models.return_value = [mock_model1, mock_model2]
        
        models = adapter.list_models()
        assert models == ["qwen2.5-coder:7b", "llama3.1:8b"]
    
    @patch("src.llm.backend_router.OllamaBackendAdapter._ensure_client")
    def test_generate(self, mock_ensure, mock_config, mock_logger):
        """Test text generation."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        adapter._client = MagicMock()
        adapter._client.default_model = "qwen2.5-coder:7b"
        adapter._client.generate.return_value = {
            "response": "Hello, World!",
            "eval_count": 5,
        }
        
        result = adapter.generate("Say hello", model="qwen2.5-coder:7b")
        
        assert isinstance(result, GenerationResult)
        assert result.text == "Hello, World!"
        assert result.backend == "ollama"
        assert result.tokens_generated == 5
    
    @patch("src.llm.backend_router.OllamaBackendAdapter._ensure_client")
    def test_chat(self, mock_ensure, mock_config, mock_logger):
        """Test chat completion."""
        adapter = OllamaBackendAdapter(mock_config, mock_logger)
        adapter._client = MagicMock()
        adapter._client.default_model = "qwen2.5-coder:7b"
        adapter._client.chat.return_value = {
            "message": {"content": "I'm doing great!"},
            "eval_count": 10,
        }
        
        messages = [
            ChatMessage(role="user", content="How are you?")
        ]
        
        result = adapter.chat(messages, model="qwen2.5-coder:7b")
        
        assert isinstance(result, GenerationResult)
        assert result.text == "I'm doing great!"
        assert result.backend == "ollama"


# ============================================================================
# BackendRouter Tests - Initialization
# ============================================================================

class TestBackendRouterInit:
    """Tests for BackendRouter initialization."""
    
    @patch("src.llm.backend_router.get_platform_info")
    @patch("src.llm.backend_router.OllamaBackendAdapter")
    def test_init_with_ollama_only(
        self, mock_ollama_cls, mock_get_platform, 
        mock_config, mock_logger, mock_platform_linux
    ):
        """Test initialization on non-Apple platform (Ollama only)."""
        mock_get_platform.return_value = mock_platform_linux
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.backend_name = "ollama"
        mock_ollama_cls.return_value = mock_ollama
        
        router = BackendRouter(mock_config, mock_logger)
        
        assert router.backend_name == "ollama"
        assert router.is_available() is True
    
    @patch("src.llm.backend_router.get_platform_info")
    @patch("src.llm.backend_router.OllamaBackendAdapter")
    def test_init_prefers_mlx_on_apple(
        self, mock_ollama_cls, mock_get_platform,
        mock_config, mock_logger, mock_platform_apple_silicon
    ):
        """Test that MLX is preferred on Apple Silicon when available."""
        mock_get_platform.return_value = mock_platform_apple_silicon
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.backend_name = "ollama"
        mock_ollama_cls.return_value = mock_ollama
        
        # Create router - MLX will be loaded since we're on Apple Silicon
        # Mock the MLXBackend import inside the router
        with patch.dict("sys.modules", {"src.llm.mlx_backend": MagicMock()}):
            with patch.object(BackendRouter, "_initialize_backends") as mock_init:
                router = BackendRouter.__new__(BackendRouter)
                router._config = mock_config
                router._logger = mock_logger
                router._platform = mock_platform_apple_silicon
                router._backend_preference = "auto"
                router._mlx_enabled = True
                
                # Setup mocks
                mock_mlx = MagicMock()
                mock_mlx.is_available.return_value = True
                mock_mlx.backend_name = "mlx"
                
                router._mlx_backend = mock_mlx
                router._ollama_backend = mock_ollama
                router._active_backend = None
                
                # Run selection
                router._select_backend()
        
        # Should prefer MLX on Apple Silicon
        assert router.backend_name == "mlx"
    
    @patch("src.llm.backend_router.get_platform_info")
    @patch("src.llm.backend_router.OllamaBackendAdapter")
    def test_init_fallback_to_ollama(
        self, mock_ollama_cls, mock_get_platform,
        mock_config, mock_logger, mock_platform_apple_silicon
    ):
        """Test fallback to Ollama when MLX unavailable."""
        mock_get_platform.return_value = mock_platform_apple_silicon
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.backend_name = "ollama"
        mock_ollama_cls.return_value = mock_ollama
        
        # Simulate MLX import failure
        with patch.object(
            BackendRouter, "_initialize_backends",
            wraps=lambda self: self._select_backend()
        ):
            router = BackendRouter.__new__(BackendRouter)
            router._config = mock_config
            router._logger = mock_logger
            router._platform = mock_platform_apple_silicon
            router._mlx_backend = None  # MLX not available
            router._ollama_backend = mock_ollama
            router._active_backend = None
            router._backend_preference = "auto"
            router._mlx_enabled = True
            router._select_backend()
        
        assert router.backend_name == "ollama"
    
    @patch("src.llm.backend_router.get_platform_info")
    @patch("src.llm.backend_router.OllamaBackendAdapter")
    def test_init_explicit_ollama_preference(
        self, mock_ollama_cls, mock_get_platform,
        mock_logger, mock_platform_apple_silicon
    ):
        """Test explicit Ollama preference ignores MLX."""
        mock_get_platform.return_value = mock_platform_apple_silicon
        
        # Config with explicit ollama preference
        mock_config = MagicMock()
        mock_config.get_section.return_value = {
            "backend": "ollama",  # Explicit preference
            "ollama": {"host": "http://localhost:11434"},
            "mlx": {"enabled": True},
        }
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.backend_name = "ollama"
        mock_ollama_cls.return_value = mock_ollama
        
        router = BackendRouter(mock_config, mock_logger)
        
        # Should use Ollama despite Apple Silicon
        assert router.backend_name == "ollama"
    
    @patch("src.llm.backend_router.get_platform_info")
    @patch("src.llm.backend_router.OllamaBackendAdapter")
    def test_init_mlx_disabled(
        self, mock_ollama_cls, mock_get_platform,
        mock_logger, mock_platform_apple_silicon
    ):
        """Test that disabled MLX falls back to Ollama."""
        mock_get_platform.return_value = mock_platform_apple_silicon
        
        # Config with MLX disabled
        mock_config = MagicMock()
        mock_config.get_section.return_value = {
            "backend": "auto",
            "ollama": {"host": "http://localhost:11434"},
            "mlx": {"enabled": False},  # MLX disabled
        }
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.backend_name = "ollama"
        mock_ollama_cls.return_value = mock_ollama
        
        router = BackendRouter(mock_config, mock_logger)
        
        # Should use Ollama since MLX is disabled
        assert router.backend_name == "ollama"


# ============================================================================
# BackendRouter Tests - Operations
# ============================================================================

class TestBackendRouterOperations:
    """Tests for BackendRouter operations."""
    
    @pytest.fixture
    def router_with_mock_backend(self, mock_config, mock_logger):
        """Create a router with mocked backend (Ollama only)."""
        # Create router manually to avoid real MLX initialization
        router = BackendRouter.__new__(BackendRouter)
        router._config = mock_config
        router._logger = mock_logger
        
        # Mock backend
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.backend_name = "ollama"
        
        router._mlx_backend = None
        router._ollama_backend = mock_backend
        router._active_backend = mock_backend
        router._platform = MagicMock(
            os="Linux",
            arch="x86_64",
            is_apple_silicon=False,
            has_mlx=False,
        )
        
        return router, mock_backend
    
    def test_generate_routes_to_backend(self, router_with_mock_backend):
        """Test that generate routes to active backend."""
        router, mock_backend = router_with_mock_backend
        
        mock_result = GenerationResult(
            text="Test output",
            model="qwen2.5-coder:7b",
            backend="ollama",
            tokens_generated=5,
        )
        mock_backend.generate.return_value = mock_result
        
        result = router.generate("Test prompt")
        
        mock_backend.generate.assert_called_once()
        assert result.text == "Test output"
    
    def test_chat_routes_to_backend(self, router_with_mock_backend):
        """Test that chat routes to active backend."""
        router, mock_backend = router_with_mock_backend
        
        mock_result = GenerationResult(
            text="Chat response",
            model="qwen2.5-coder:7b",
            backend="ollama",
            tokens_generated=10,
        )
        mock_backend.chat.return_value = mock_result
        
        messages = [ChatMessage(role="user", content="Hello")]
        result = router.chat(messages)
        
        mock_backend.chat.assert_called_once()
        assert result.text == "Chat response"
    
    def test_list_models(self, router_with_mock_backend):
        """Test listing models from active backend."""
        router, mock_backend = router_with_mock_backend
        mock_backend.list_models.return_value = ["model1", "model2"]
        
        models = router.list_models()
        
        assert models == ["model1", "model2"]
    
    def test_generate_raises_when_no_backend(self, mock_config, mock_logger):
        """Test that generate raises when no backend available."""
        router = BackendRouter.__new__(BackendRouter)
        router._active_backend = None
        
        with pytest.raises(RuntimeError, match="No LLM backend available"):
            router.generate("Test prompt")
    
    def test_chat_raises_when_no_backend(self, mock_config, mock_logger):
        """Test that chat raises when no backend available."""
        router = BackendRouter.__new__(BackendRouter)
        router._active_backend = None
        
        with pytest.raises(RuntimeError, match="No LLM backend available"):
            router.chat([ChatMessage(role="user", content="Hello")])


# ============================================================================
# BackendRouter Tests - Backend Management
# ============================================================================

class TestBackendRouterManagement:
    """Tests for backend management operations."""
    
    def test_switch_to_ollama(self, mock_config, mock_logger):
        """Test switching to Ollama backend."""
        router = BackendRouter.__new__(BackendRouter)
        router._logger = mock_logger
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.backend_name = "ollama"
        router._ollama_backend = mock_ollama
        router._mlx_backend = None
        router._active_backend = None
        
        success = router.switch_backend("ollama")
        
        assert success is True
        assert router._active_backend == mock_ollama
    
    def test_switch_to_unavailable_backend(self, mock_config, mock_logger):
        """Test switching to unavailable backend fails."""
        router = BackendRouter.__new__(BackendRouter)
        router._logger = mock_logger
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        router._ollama_backend = mock_ollama
        router._mlx_backend = None
        router._active_backend = None
        
        success = router.switch_backend("ollama")
        
        assert success is False
    
    def test_switch_to_unknown_backend(self, mock_config, mock_logger):
        """Test switching to unknown backend fails."""
        router = BackendRouter.__new__(BackendRouter)
        router._logger = mock_logger
        
        success = router.switch_backend("unknown")
        
        assert success is False
    
    def test_get_backends_status(self, mock_config, mock_logger):
        """Test getting backends status."""
        router = BackendRouter.__new__(BackendRouter)
        router._logger = mock_logger
        router._platform = MagicMock(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_mlx=True,
        )
        
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        router._ollama_backend = mock_ollama
        router._mlx_backend = None
        router._active_backend = mock_ollama
        mock_ollama.backend_name = "ollama"
        
        status = router.get_backends_status()
        
        assert status["active"] == "ollama"
        assert status["platform"]["os"] == "macOS"
        assert status["backends"]["ollama"]["available"] is True
        assert status["backends"]["ollama"]["active"] is True
        assert status["backends"]["mlx"]["available"] is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestBackendRouterIntegration:
    """Integration tests (require mocking at module level)."""
    
    def test_full_workflow_generate(self, mock_config, mock_logger):
        """Test complete generate workflow."""
        with patch("src.llm.backend_router.get_platform_info") as mock_platform:
            mock_platform.return_value = MagicMock(
                os="Linux",
                arch="x86_64",
                is_apple_silicon=False,
                has_mlx=False,
            )
            
            with patch("src.llm.backend_router.OllamaBackendAdapter") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.is_available.return_value = True
                mock_backend.backend_name = "ollama"
                mock_backend.generate.return_value = GenerationResult(
                    text="Generated text",
                    model="qwen2.5-coder:7b",
                    backend="ollama",
                    tokens_generated=10,
                    generation_time_ms=500.0,
                    tokens_per_second=20.0,
                )
                mock_cls.return_value = mock_backend
                
                router = BackendRouter(mock_config, mock_logger)
                result = router.generate("Test prompt", max_tokens=100)
                
                assert result.text == "Generated text"
                assert result.backend == "ollama"
    
    def test_full_workflow_chat(self, mock_config, mock_logger):
        """Test complete chat workflow."""
        with patch("src.llm.backend_router.get_platform_info") as mock_platform:
            mock_platform.return_value = MagicMock(
                os="Linux",
                arch="x86_64",
                is_apple_silicon=False,
                has_mlx=False,
            )
            
            with patch("src.llm.backend_router.OllamaBackendAdapter") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.is_available.return_value = True
                mock_backend.backend_name = "ollama"
                mock_backend.chat.return_value = GenerationResult(
                    text="Chat response",
                    model="qwen2.5-coder:7b",
                    backend="ollama",
                    tokens_generated=15,
                )
                mock_cls.return_value = mock_backend
                
                router = BackendRouter(mock_config, mock_logger)
                
                messages = [
                    ChatMessage(role="system", content="You are helpful."),
                    ChatMessage(role="user", content="Hello!"),
                ]
                result = router.chat(messages)
                
                assert result.text == "Chat response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
