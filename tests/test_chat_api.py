"""
Unit tests for chat API endpoints.

Tests the /api/chat (Ollama-compatible) and /v1/chat/completions (OpenAI-compatible)
endpoints with mocked OllamaClient and RAGEngine dependencies.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timezone

from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    with patch("src.api.routes.chat.get_ollama_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


@pytest.fixture
def mock_rag_engine():
    """Create a mock RAGEngine."""
    with patch("src.api.routes.chat.get_rag_engine") as mock_get:
        engine = MagicMock()
        mock_get.return_value = engine
        yield engine


@pytest.fixture
def mock_context_docs():
    """Create mock context documents."""
    from src.llm.rag_engine import ContextDocument
    return [
        ContextDocument(
            id="doc1",
            path="/test/file1.md",
            title="Test Document 1",
            content="This is test content for document 1.",
            score=0.95,
            category="documentation",
        ),
        ContextDocument(
            id="doc2",
            path="/test/file2.py",
            title="Test Document 2",
            content="def hello(): return 'world'",
            score=0.85,
            category="code",
        ),
    ]


@pytest.fixture
def chat_app():
    """Create test client for the main app."""
    # Need to reset global state
    import src.api.routes.chat as chat_module
    chat_module._ollama_client = None
    chat_module._rag_engine = None
    
    from src.api.main import app
    return TestClient(app)


# ============================================================================
# /api/chat Endpoint Tests
# ============================================================================

class TestChatEndpoint:
    """Tests for /api/chat (Ollama-compatible)."""
    
    def test_chat_basic_request(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test basic chat request."""
        # Setup mock
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Hello! How can I help?"},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Hello"}],
            [],
            ""
        )
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "qwen2.5-coder:7b"
        assert data["message"]["role"] == "assistant"
        assert "Hello" in data["message"]["content"]
        assert data["done"] is True
    
    def test_chat_with_rag_context(self, chat_app, mock_ollama_client, mock_rag_engine, mock_context_docs):
        """Test chat with RAG context enrichment."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Based on the docs..."},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [
                {"role": "system", "content": "Context: test content"},
                {"role": "user", "content": "What does the doc say?"},
            ],
            mock_context_docs,
            "Context: test content",
        )
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "What does the doc say?"}],
            "stream": False,
            "rag_enabled": True,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["rag_context"] is not None
        assert len(data["rag_context"]) == 2
        assert data["rag_context"][0]["id"] == "doc1"
        assert data["rag_context"][0]["score"] == 0.95
    
    def test_chat_rag_disabled(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test chat with RAG disabled."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Simple response"},
            "done": True,
        }
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
            "rag_enabled": False,
        })
        
        assert response.status_code == 200
        data = response.json()
        # RAG engine should not be called
        mock_rag_engine.enrich_messages.assert_not_called()
        assert data["rag_context"] is None
    
    def test_chat_multiple_messages(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test chat with multiple messages (conversation)."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Here's the answer..."},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "What is Python?"},
            ],
            [],
            "",
        )
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "What is Python?"},
            ],
            "stream": False,
        })
        
        assert response.status_code == 200
        # Verify all messages were passed
        call_args = mock_rag_engine.enrich_messages.call_args
        assert len(call_args[0][0]) == 3
    
    def test_chat_with_options(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test chat with model options."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Creative response"},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Be creative"}],
            [],
            "",
        )
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Be creative"}],
            "stream": False,
            "options": {"temperature": 0.9, "top_p": 0.95},
        })
        
        assert response.status_code == 200
        # Verify options passed to Ollama
        call_args = mock_ollama_client.chat.call_args
        assert call_args[1].get("options") == {"temperature": 0.9, "top_p": 0.95}
    
    def test_chat_ollama_connection_error(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test handling of Ollama connection error."""
        from src.llm.ollama_client import OllamaConnectionError
        mock_ollama_client.chat.side_effect = OllamaConnectionError("Cannot connect")
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Hello"}],
            [],
            "",
        )
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        })
        
        assert response.status_code == 503
        assert "unavailable" in response.json()["message"].lower()
    
    def test_chat_model_not_found(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test handling of model not found error."""
        from src.llm.ollama_client import OllamaModelNotFound
        mock_ollama_client.chat.side_effect = OllamaModelNotFound("unknown-model")
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Hello"}],
            [],
            "",
        )
        
        response = chat_app.post("/api/chat", json={
            "model": "unknown-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        })
        
        assert response.status_code == 404
        assert "unknown-model" in response.json()["message"]
    
    def test_chat_rag_failure_graceful(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test graceful handling when RAG fails."""
        mock_rag_engine.enrich_messages.side_effect = Exception("RAG error")
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Response without RAG"},
            "done": True,
        }
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        })
        
        # Should succeed even if RAG fails
        assert response.status_code == 200


# ============================================================================
# /v1/chat/completions Endpoint Tests (OpenAI-compatible)
# ============================================================================

class TestOpenAIChatEndpoint:
    """Tests for /v1/chat/completions (OpenAI-compatible)."""
    
    def test_openai_basic_request(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test basic OpenAI-format chat request."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Hello there!"},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Hello"}],
            [],
            "",
        )
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert "id" in data
        assert data["model"] == "qwen2.5-coder:7b"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert data["choices"][0]["finish_reason"] == "stop"
    
    def test_openai_with_temperature(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test OpenAI request with temperature parameter."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Response"},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Test"}],
            [],
            "",
        )
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Test"}],
            "temperature": 0.7,
        })
        
        assert response.status_code == 200
        # Verify temperature passed to Ollama
        call_args = mock_ollama_client.chat.call_args
        assert call_args[1].get("options", {}).get("temperature") == 0.7
    
    def test_openai_with_max_tokens(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test OpenAI request with max_tokens parameter."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Short"},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Test"}],
            [],
            "",
        )
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 100,
        })
        
        assert response.status_code == 200
        # max_tokens should be converted to num_predict for Ollama
        call_args = mock_ollama_client.chat.call_args
        assert call_args[1].get("options", {}).get("num_predict") == 100
    
    def test_openai_response_format(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test OpenAI response has correct format."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Response content"},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Test"}],
            [],
            "",
        )
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Test"}],
        })
        
        data = response.json()
        
        # Verify OpenAI format
        assert "id" in data
        assert data["id"].startswith("chatcmpl-")
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert isinstance(data["created"], int)
        assert data["choices"][0]["index"] == 0
    
    def test_openai_with_rag_context(self, chat_app, mock_ollama_client, mock_rag_engine, mock_context_docs):
        """Test OpenAI response includes RAG context extension."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Based on context..."},
            "done": True,
        }
        mock_rag_engine.enrich_messages.return_value = (
            [
                {"role": "system", "content": "Context info"},
                {"role": "user", "content": "Question"},
            ],
            mock_context_docs,
            "Context info",
        )
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Question"}],
            "rag_enabled": True,
        })
        
        data = response.json()
        assert data["rag_context"] is not None
        assert len(data["rag_context"]) == 2
    
    def test_openai_rag_disabled(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test OpenAI request with RAG disabled."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Response"},
            "done": True,
        }
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "rag_enabled": False,
        })
        
        assert response.status_code == 200
        mock_rag_engine.enrich_messages.assert_not_called()
    
    def test_openai_connection_error(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test OpenAI endpoint handles connection error."""
        from src.llm.ollama_client import OllamaConnectionError
        mock_ollama_client.chat.side_effect = OllamaConnectionError("Ollama down")
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Hello"}],
            [],
            "",
        )
        
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        
        assert response.status_code == 503


# ============================================================================
# Request Validation Tests
# ============================================================================

class TestRequestValidation:
    """Tests for request validation."""
    
    def test_missing_model(self, chat_app):
        """Test request without model field."""
        response = chat_app.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}],
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_messages(self, chat_app):
        """Test request without messages field."""
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
        })
        
        assert response.status_code == 422
    
    def test_empty_messages(self, chat_app, mock_ollama_client, mock_rag_engine):
        """Test request with empty messages array."""
        mock_rag_engine.enrich_messages.return_value = ([], [], "")
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": ""},
            "done": True,
        }
        
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [],
            "stream": False,
        })
        
        # Empty messages should still work (model handles it)
        assert response.status_code == 200
    
    def test_invalid_message_format(self, chat_app):
        """Test request with invalid message format."""
        response = chat_app.post("/api/chat", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"invalid": "format"}],
        })
        
        assert response.status_code == 422
    
    def test_openai_invalid_temperature(self, chat_app):
        """Test OpenAI request with invalid temperature."""
        response = chat_app.post("/v1/chat/completions", json={
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 3.0,  # Invalid: max is 2
        })
        
        assert response.status_code == 422


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_context_docs_to_dict(self, mock_context_docs):
        """Test conversion of ContextDocument to dict."""
        from src.api.routes.chat import context_docs_to_dict
        
        result = context_docs_to_dict(mock_context_docs)
        
        assert len(result) == 2
        assert result[0]["id"] == "doc1"
        assert result[0]["path"] == "/test/file1.md"
        assert result[0]["score"] == 0.95
        assert result[0]["category"] == "documentation"
        assert "content" not in result[0]  # Content should not be included
    
    def test_context_docs_to_dict_empty(self):
        """Test conversion with empty list."""
        from src.api.routes.chat import context_docs_to_dict
        
        result = context_docs_to_dict([])
        assert result == []
