"""
Unit tests for models API endpoints.

Tests the /api/tags (Ollama-compatible) and /v1/models (OpenAI-compatible)
endpoints with mocked OllamaClient dependency.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    with patch("src.api.routes.models.get_ollama_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


@pytest.fixture
def mock_models_list():
    """Create mock models data from Ollama."""
    return {
        "models": [
            {
                "name": "qwen2.5-coder:7b",
                "modified_at": "2026-01-28T12:00:00Z",
                "size": 4500000000,
                "digest": "sha256:abc123",
                "details": {
                    "format": "gguf",
                    "family": "qwen2",
                    "parameter_size": "7B",
                    "quantization_level": "Q4_K_M",
                },
            },
            {
                "name": "llama3.1:8b",
                "modified_at": "2026-01-25T10:00:00Z",
                "size": 5000000000,
                "digest": "sha256:def456",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "parameter_size": "8B",
                    "quantization_level": "Q4_K_M",
                },
            },
        ]
    }


@pytest.fixture
def models_app():
    """Create test client for the main app."""
    # Reset global state
    import src.api.routes.models as models_module
    models_module._ollama_client = None
    
    from src.api.main import app
    return TestClient(app)


# ============================================================================
# /api/tags Endpoint Tests (Ollama-compatible)
# ============================================================================

class TestOllamaModelsEndpoint:
    """Tests for /api/tags (Ollama-compatible)."""
    
    def test_list_models_basic(self, models_app, mock_ollama_client, mock_models_list):
        """Test basic model listing."""
        mock_ollama_client.list_models.return_value = mock_models_list
        
        response = models_app.get("/api/tags")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2
    
    def test_list_models_format(self, models_app, mock_ollama_client, mock_models_list):
        """Test model response format."""
        mock_ollama_client.list_models.return_value = mock_models_list
        
        response = models_app.get("/api/tags")
        data = response.json()
        
        model = data["models"][0]
        assert model["name"] == "qwen2.5-coder:7b"
        assert model["size"] == 4500000000
        assert model["digest"] == "sha256:abc123"
        assert model["modified_at"] == "2026-01-28T12:00:00Z"
    
    def test_list_models_with_details(self, models_app, mock_ollama_client, mock_models_list):
        """Test model details are included."""
        mock_ollama_client.list_models.return_value = mock_models_list
        
        response = models_app.get("/api/tags")
        data = response.json()
        
        details = data["models"][0]["details"]
        assert details is not None
        assert details["format"] == "gguf"
        assert details["family"] == "qwen2"
        assert details["parameter_size"] == "7B"
        assert details["quantization_level"] == "Q4_K_M"
    
    def test_list_models_empty(self, models_app, mock_ollama_client):
        """Test empty models list."""
        mock_ollama_client.list_models.return_value = {"models": []}
        
        response = models_app.get("/api/tags")
        
        assert response.status_code == 200
        data = response.json()
        assert data["models"] == []
    
    def test_list_models_connection_error(self, models_app, mock_ollama_client):
        """Test handling of Ollama connection error."""
        from src.llm.ollama_client import OllamaConnectionError
        mock_ollama_client.list_models.side_effect = OllamaConnectionError("Cannot connect")
        
        response = models_app.get("/api/tags")
        
        assert response.status_code == 503
        assert "unavailable" in response.json()["message"].lower()
    
    def test_show_model_info(self, models_app, mock_ollama_client):
        """Test getting specific model info."""
        mock_ollama_client.show_model.return_value = {
            "modelfile": "FROM qwen2.5-coder:7b",
            "parameters": "temperature 0.7",
            "template": "{{ .Prompt }}",
        }
        
        response = models_app.get("/api/show/qwen2.5-coder:7b")
        
        assert response.status_code == 200
        data = response.json()
        assert "modelfile" in data
    
    def test_show_model_not_found(self, models_app, mock_ollama_client):
        """Test model not found error."""
        mock_ollama_client.show_model.side_effect = Exception("Model not found")
        
        response = models_app.get("/api/show/nonexistent-model")
        
        assert response.status_code == 404


# ============================================================================
# /v1/models Endpoint Tests (OpenAI-compatible)
# ============================================================================

class TestOpenAIModelsEndpoint:
    """Tests for /v1/models (OpenAI-compatible)."""
    
    def test_list_models_openai_format(self, models_app, mock_ollama_client, mock_models_list):
        """Test OpenAI format model listing."""
        mock_ollama_client.list_models.return_value = mock_models_list
        
        response = models_app.get("/v1/models")
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) == 2
    
    def test_list_models_openai_model_format(self, models_app, mock_ollama_client, mock_models_list):
        """Test individual model format in OpenAI response."""
        mock_ollama_client.list_models.return_value = mock_models_list
        
        response = models_app.get("/v1/models")
        data = response.json()
        
        model = data["data"][0]
        assert model["id"] == "qwen2.5-coder:7b"
        assert model["object"] == "model"
        assert "created" in model
        assert isinstance(model["created"], int)
        assert model["owned_by"] == "ollama"
    
    def test_list_models_openai_empty(self, models_app, mock_ollama_client):
        """Test empty models list in OpenAI format."""
        mock_ollama_client.list_models.return_value = {"models": []}
        
        response = models_app.get("/v1/models")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
    
    def test_list_models_openai_connection_error(self, models_app, mock_ollama_client):
        """Test connection error in OpenAI endpoint."""
        from src.llm.ollama_client import OllamaConnectionError
        mock_ollama_client.list_models.side_effect = OllamaConnectionError("Down")
        
        response = models_app.get("/v1/models")
        
        assert response.status_code == 503
    
    def test_get_single_model_openai(self, models_app, mock_ollama_client):
        """Test getting single model in OpenAI format."""
        mock_ollama_client.show_model.return_value = {
            "modelfile": "FROM qwen2.5-coder:7b"
        }
        
        response = models_app.get("/v1/models/qwen2.5-coder:7b")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "qwen2.5-coder:7b"
        assert data["object"] == "model"
    
    def test_get_model_not_found_openai(self, models_app, mock_ollama_client):
        """Test model not found in OpenAI endpoint."""
        mock_ollama_client.show_model.side_effect = Exception("Not found")
        
        response = models_app.get("/v1/models/nonexistent")
        
        assert response.status_code == 404
