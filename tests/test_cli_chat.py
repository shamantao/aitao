"""
Unit tests for CLI chat module.

Tests the interactive chat session, command handling, and RAG integration.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from io import StringIO
import json


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    with patch("src.cli.chat.OllamaClient") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        yield client


@pytest.fixture
def mock_rag_engine():
    """Create a mock RAGEngine."""
    with patch("src.cli.chat.RAGEngine") as MockEngine:
        engine = MagicMock()
        MockEngine.return_value = engine
        # Default behavior: return messages unchanged, no context
        engine.enrich_messages.return_value = (
            [{"role": "user", "content": "test"}],
            [],
            "",
        )
        yield engine


@pytest.fixture
def mock_config():
    """Create a mock ConfigManager via get_config singleton."""
    with patch("src.cli.chat.get_config") as MockGetConfig:
        config = MagicMock()
        config.get.return_value = "test-model:7b"
        MockGetConfig.return_value = config
        yield config


@pytest.fixture
def mock_path_manager(tmp_path):
    """Create a mock path_manager."""
    with patch("src.cli.chat.path_manager") as mock_pm:
        mock_pm.get_storage_root.return_value = tmp_path
        yield mock_pm


# ============================================================================
# ChatSession Tests
# ============================================================================

class TestChatSession:
    """Tests for ChatSession class."""
    
    def test_session_initialization(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test chat session initializes correctly."""
        from src.cli.chat import ChatSession
        
        session = ChatSession(show_context=False, save_history=False)
        
        assert session.model == "test-model:7b"
        assert session.messages == []
        assert session.session_id is not None
    
    def test_add_system_message(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test adding system message."""
        from src.cli.chat import ChatSession
        
        session = ChatSession(show_context=False, save_history=False)
        session.add_system_message("You are a helpful assistant.")
        
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "system"
        assert "helpful assistant" in session.messages[0]["content"]
    
    def test_chat_adds_messages(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test chat adds user and assistant messages."""
        from src.cli.chat import ChatSession
        
        # Setup mock streaming response
        mock_ollama_client.chat.return_value = iter([
            json.dumps({"message": {"content": "Hello "}, "done": False}),
            json.dumps({"message": {"content": "there!"}, "done": True}),
        ])
        
        mock_rag_engine.enrich_messages.return_value = (
            [{"role": "user", "content": "Hi"}],
            [],
            "",
        )
        
        session = ChatSession(show_context=False, save_history=False)
        response = session.chat("Hi")
        
        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "Hi"
        assert session.messages[1]["role"] == "assistant"
        assert "Hello" in session.messages[1]["content"]
    
    def test_chat_with_rag_context(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test chat with RAG context enrichment."""
        from src.cli.chat import ChatSession
        from src.llm.rag_engine import ContextDocument
        
        # Mock context documents
        mock_docs = [
            ContextDocument(
                id="doc1",
                path="/test/file.py",
                title="Test File",
                content="test content",
                score=0.95,
            ),
        ]
        
        mock_rag_engine.enrich_messages.return_value = (
            [
                {"role": "system", "content": "Context: test content"},
                {"role": "user", "content": "What is this?"},
            ],
            mock_docs,
            "Context: test content",
        )
        
        mock_ollama_client.chat.return_value = iter([
            json.dumps({"message": {"content": "It's a test."}, "done": True}),
        ])
        
        session = ChatSession(show_context=True, save_history=False)
        session.chat("What is this?")
        
        # Verify RAG was called
        mock_rag_engine.enrich_messages.assert_called_once()
    
    def test_get_stats(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test session statistics."""
        from src.cli.chat import ChatSession
        
        session = ChatSession(show_context=False, save_history=False)
        session.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        
        stats = session.get_stats()
        
        assert stats["message_count"] == 2
        assert stats["model"] == "test-model:7b"
        assert "session_id" in stats
        assert "duration_seconds" in stats
    
    def test_save_history(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager, tmp_path
    ):
        """Test conversation history is saved."""
        from src.cli.chat import ChatSession
        
        session = ChatSession(show_context=False, save_history=True)
        session.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        session._save_history()
        
        # Check file was created
        assert session.history_file.exists()
        
        # Verify content
        with open(session.history_file) as f:
            data = json.load(f)
        
        assert len(data["messages"]) == 2
        assert data["model"] == "test-model:7b"


# ============================================================================
# Colors Tests
# ============================================================================

class TestColors:
    """Tests for terminal colors."""
    
    def test_colors_class_exists(self):
        """Test Colors class exists with expected attributes."""
        from src.cli.chat import Colors
        
        # Check attributes exist (may be empty strings if TTY detection disabled)
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "RESET")
        assert hasattr(Colors, "BOLD")
    
    def test_colors_disable(self):
        """Test colors can be disabled."""
        from src.cli.chat import Colors
        
        # Disable colors
        Colors.disable()
        
        # After disable, all should be empty
        assert Colors.RED == ""
        assert Colors.GREEN == ""
        assert Colors.RESET == ""


# ============================================================================
# Command Handling Tests
# ============================================================================

class TestCommandHandling:
    """Tests for CLI command handling."""
    
    def test_quit_commands(self):
        """Test quit commands are recognized."""
        quit_commands = ["/quit", "/exit", "/q"]
        
        for cmd in quit_commands:
            assert cmd.lower().split()[0] in ("/quit", "/exit", "/q")
    
    def test_help_commands(self):
        """Test help commands are recognized."""
        help_commands = ["/help", "/?"]
        
        for cmd in help_commands:
            assert cmd.lower().split()[0] in ("/help", "/?")
    
    def test_context_toggle_on(self):
        """Test context command parsing - on."""
        cmd = "/context on"
        parts = cmd.lower().split()
        
        assert parts[0] == "/context"
        assert len(parts) > 1
        assert parts[1] != "off"
    
    def test_context_toggle_off(self):
        """Test context command parsing - off."""
        cmd = "/context off"
        parts = cmd.lower().split()
        
        assert parts[0] == "/context"
        assert len(parts) > 1
        assert parts[1] == "off"
    
    def test_model_command_with_arg(self):
        """Test model command with argument."""
        cmd = "/model llama3.1:8b"
        parts = cmd.split()
        
        assert parts[0] == "/model"
        assert parts[1] == "llama3.1:8b"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for CLI chat."""
    
    def test_multi_turn_conversation(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test multi-turn conversation maintains history."""
        from src.cli.chat import ChatSession
        
        # Setup mock responses
        mock_ollama_client.chat.return_value = iter([
            json.dumps({"message": {"content": "Response"}, "done": True}),
        ])
        
        session = ChatSession(show_context=False, save_history=False)
        
        # First turn
        session.chat("Hello")
        assert len(session.messages) == 2
        
        # Second turn
        mock_ollama_client.chat.return_value = iter([
            json.dumps({"message": {"content": "Response 2"}, "done": True}),
        ])
        session.chat("How are you?")
        assert len(session.messages) == 4
        
        # Third turn
        mock_ollama_client.chat.return_value = iter([
            json.dumps({"message": {"content": "Response 3"}, "done": True}),
        ])
        session.chat("Thanks!")
        assert len(session.messages) == 6
    
    def test_connection_error_handling(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test handling of Ollama connection error."""
        from src.cli.chat import ChatSession
        from src.llm.ollama_client import OllamaConnectionError
        
        mock_ollama_client.chat.side_effect = OllamaConnectionError("Cannot connect")
        
        session = ChatSession(show_context=False, save_history=False)
        response = session.chat("Hello")
        
        assert "Error" in response
    
    def test_model_not_found_handling(
        self, mock_ollama_client, mock_rag_engine, mock_config, mock_path_manager
    ):
        """Test handling of model not found error."""
        from src.cli.chat import ChatSession
        from src.llm.ollama_client import OllamaModelNotFound
        
        mock_ollama_client.chat.side_effect = OllamaModelNotFound("unknown-model")
        
        session = ChatSession(show_context=False, save_history=False)
        response = session.chat("Hello")
        
        assert "Error" in response
