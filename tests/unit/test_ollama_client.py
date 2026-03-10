"""
Unit tests for OllamaClient.

Tests cover:
- Connection management
- Model listing
- Chat completion (sync and stream)
- Text generation
- Embeddings
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import httpx
import json

from src.llm.ollama_client import (
    OllamaClient,
    OllamaModel,
    OllamaChatMessage,
    OllamaConnectionError,
    OllamaModelNotFound,
)


@pytest.fixture
def mock_config():
    """Mock ConfigManager."""
    config = Mock()
    config.get_section.return_value = {
        "ollama": {
            "host": "http://localhost:11434",
            "default_model": "qwen2.5-coder:7b"
        }
    }
    return config


@pytest.fixture
def mock_logger():
    """Mock Logger."""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def ollama_client(mock_config, mock_logger):
    """Create OllamaClient instance with mocked HTTP clients."""
    client = OllamaClient(mock_config, mock_logger)
    # Replace HTTP clients with mocks
    client.client = Mock()
    client.async_client = Mock()
    return client


class TestOllamaClientInit:
    """Test OllamaClient initialization."""
    
    def test_init_success(self, mock_config, mock_logger):
        """Test successful initialization."""
        client = OllamaClient(mock_config, mock_logger)
        assert client.host == "http://localhost:11434"
        assert client.default_model == "qwen2.5-coder:7b"
        mock_logger.info.assert_called()
    
    def test_init_missing_config(self, mock_logger):
        """Test initialization with missing llm config."""
        config = Mock()
        config.get_section.return_value = None
        
        with pytest.raises(ValueError, match="Missing 'llm' section"):
            OllamaClient(config, mock_logger)


class TestOllamaClientConnection:
    """Test connection management."""
    
    def test_check_connection_success(self, ollama_client):
        """Test successful connection check."""
        mock_response = Mock()
        mock_response.status_code = 200
        ollama_client.client.get.return_value = mock_response
        
        result = ollama_client._check_connection()
        assert result is True
    
    def test_check_connection_failure(self, ollama_client):
        """Test failed connection check."""
        ollama_client.client.get.side_effect = Exception("Connection refused")
        
        result = ollama_client._check_connection()
        assert result is False
    
    def test_is_healthy(self, ollama_client):
        """Test health check."""
        ollama_client._check_connection = Mock(return_value=True)
        assert ollama_client.is_healthy() is True


class TestOllamaClientModels:
    """Test model listing."""
    
    def test_list_models_success(self, ollama_client):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "qwen2.5-coder:7b",
                    "size": 4700000000,
                    "digest": "abc123",
                    "modified_at": "2026-01-28T10:00:00Z"
                },
                {
                    "name": "llama3.1:8b",
                    "size": 5000000000,
                    "digest": "def456",
                    "modified_at": "2026-01-28T10:00:00Z"
                }
            ]
        }
        ollama_client.client.get.return_value = mock_response
        
        models = ollama_client.list_models()
        assert len(models) == 2
        assert models[0].name == "qwen2.5-coder:7b"
        assert models[1].name == "llama3.1:8b"
    
    def test_list_models_connection_error(self, ollama_client):
        """Test model listing with connection error."""
        ollama_client.client.get.side_effect = httpx.ConnectError("Connection refused")
        
        with pytest.raises(OllamaConnectionError):
            ollama_client.list_models()
    
    def test_list_models_bad_status(self, ollama_client):
        """Test model listing with bad HTTP status."""
        mock_response = Mock()
        mock_response.status_code = 500
        ollama_client.client.get.return_value = mock_response
        
        with pytest.raises(OllamaConnectionError):
            ollama_client.list_models()
    
    def test_get_model_info_success(self, ollama_client):
        """Test getting model info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "qwen2.5-coder:7b",
            "model": "qwen2.5-coder:7b",
            "modified_at": "2026-01-28T10:00:00Z",
            "size": 4700000000,
            "digest": "abc123",
            "details": {
                "format": "gguf",
                "family": "qwen2",
                "families": ["qwen2"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M"
            }
        }
        ollama_client.client.post.return_value = mock_response
        
        info = ollama_client.get_model_info("qwen2.5-coder:7b")
        assert info["name"] == "qwen2.5-coder:7b"
        assert info["size"] == 4700000000


class TestOllamaClientChat:
    """Test chat completion."""
    
    def test_chat_sync_success(self, ollama_client):
        """Test synchronous chat completion."""
        # Mock list_models to avoid connection
        ollama_client.list_models = Mock(return_value=[
            OllamaModel("qwen2.5-coder:7b", 0, "", "")
        ])
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "Hello!"},
            "model": "qwen2.5-coder:7b",
            "created_at": "2026-01-28T10:00:00Z",
            "done": True
        }
        ollama_client.client.post.return_value = mock_response
        
        messages = [OllamaChatMessage("user", "Hi there!")]
        response = ollama_client.chat(messages, stream=False)
        
        assert response["message"]["content"] == "Hello!"
    
    def test_chat_model_not_found(self, ollama_client):
        """Test chat with unavailable model."""
        ollama_client.list_models = Mock(return_value=[])
        
        messages = [OllamaChatMessage("user", "Hi!")]
        with pytest.raises(OllamaModelNotFound):
            ollama_client.chat(messages, model="unknown:7b")
    
    def test_chat_default_model(self, ollama_client):
        """Test chat uses default model."""
        ollama_client.list_models = Mock(return_value=[
            OllamaModel("qwen2.5-coder:7b", 0, "", "")
        ])
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Response"}}
        ollama_client.client.post.return_value = mock_response
        
        messages = [OllamaChatMessage("user", "Hi!")]
        ollama_client.chat(messages)
        
        # Verify default model was used
        call_args = ollama_client.client.post.call_args
        assert call_args[1]["json"]["model"] == "qwen2.5-coder:7b"


class TestOllamaClientGenerate:
    """Test text generation."""
    
    def test_generate_sync_success(self, ollama_client):
        """Test synchronous text generation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "qwen2.5-coder:7b",
            "response": "Generated text...",
            "done": True
        }
        ollama_client.client.post.return_value = mock_response
        
        response = ollama_client.generate("Hello", stream=False)
        assert response["response"] == "Generated text..."
    
    def test_generate_connection_error(self, ollama_client):
        """Test generate with connection error."""
        ollama_client.client.post.side_effect = httpx.ConnectError("Connection refused")
        
        with pytest.raises(OllamaConnectionError):
            ollama_client.generate("Hello", stream=False)


class TestOllamaClientEmbeddings:
    """Test embeddings generation."""
    
    def test_embeddings_success(self, ollama_client):
        """Test successful embedding generation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3, 0.4]
        }
        ollama_client.client.post.return_value = mock_response
        
        embedding = ollama_client.embeddings("Hello world")
        assert embedding == [0.1, 0.2, 0.3, 0.4]
    
    def test_embeddings_bad_status(self, ollama_client):
        """Test embeddings with bad HTTP status."""
        mock_response = Mock()
        mock_response.status_code = 400
        ollama_client.client.post.return_value = mock_response
        
        with pytest.raises(OllamaConnectionError):
            ollama_client.embeddings("Hello world")


class TestOllamaClientCleanup:
    """Test resource cleanup."""
    
    def test_context_manager(self, ollama_client):
        """Test context manager."""
        ollama_client.close = Mock()
        
        with ollama_client:
            pass
        
        ollama_client.close.assert_called_once()
    
    def test_close(self, ollama_client):
        """Test close method."""
        ollama_client.client.close = Mock()
        ollama_client.close()
        ollama_client.client.close.assert_called_once()
