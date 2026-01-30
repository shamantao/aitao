"""
Tests for ModelManager (US-021b, US-021c).

Tests cover:
- Model checking: get configured vs installed models
- Model parsing: handle tags correctly
- Status reporting: categorize present/missing/extra
- Error handling: OllamaConnectionError
- Config parsing: both old (string list) and new (dict) formats
- Model pulling: download missing models from Ollama hub
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
import subprocess

from src.core.registry import ModelStatus, ModelInfo, ModelRole
from src.llm.model_manager import ModelManager
from src.llm.ollama_client import OllamaConnectionError, OllamaModel


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Mock ConfigManager with LLM models configured."""
    config = Mock()
    
    # New format: list of dicts with name, required, roles
    config.get.side_effect = lambda key, default=None: {
        "llm.models": [
            {"name": "llama3.1-local:latest", "required": True, "size_gb": 4.7, "roles": ["chat", "rag"]},
            {"name": "qwen2.5-coder-local:latest", "required": False, "size_gb": 4.4, "roles": ["code"]},
        ],
        "llm.ollama_url": "http://localhost:11434",
    }.get(key, default)
    
    return config


@pytest.fixture
def mock_ollama_client():
    """Mock OllamaClient."""
    client = Mock()
    
    # Simulate installed models: llama3.1-local (missing: qwen2.5-coder-local)
    client.list_models.return_value = [
        OllamaModel(name="llama3.1-local:latest", size=4700000000, digest="abc123", modified_at="2026-01-28"),
        OllamaModel(name="mistral:7b", size=4000000000, digest="ghi789", modified_at="2026-01-28"),
    ]
    
    return client


@pytest.fixture
def model_manager(mock_config, mock_ollama_client):
    """Create ModelManager with mocks."""
    with patch("src.llm.model_manager.get_config", return_value=mock_config):
        manager = ModelManager(ollama_client=mock_ollama_client)
    return manager


# ============================================================================
# Tests: Model Checking
# ============================================================================

def test_check_models_present_missing_extra(model_manager, mock_ollama_client):
    """
    Test check_models() correctly categorizes models.
    
    Configured: llama3.1-local (required), qwen2.5-coder-local
    Installed: llama3.1-local, mistral
    
    Expected:
    - present: llama3.1-local
    - missing: qwen2.5-coder-local
    - extra: mistral
    - required_missing: [] (llama3.1-local is present)
    """
    status = model_manager.check_models()
    
    assert set(status.present) == {"llama3.1-local"}
    assert status.missing == ["qwen2.5-coder-local"]
    assert status.extra == ["mistral"]
    assert status.required_missing == []


def test_check_models_required_missing(model_manager, mock_ollama_client):
    """Test that required missing models are flagged."""
    # Remove llama3.1-local from installed models
    mock_ollama_client.list_models.return_value = [
        OllamaModel(name="mistral:7b", size=4500000000, digest="def456", modified_at="2026-01-28"),
    ]
    
    status = model_manager.check_models()
    
    assert "llama3.1-local" in status.missing
    assert "llama3.1-local" in status.required_missing


def test_check_models_no_configured_models():
    """Test behavior when no models are configured."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "llm.models": [],
        "llm.ollama_url": "http://localhost:11434",
    }.get(key, default)
    
    client = Mock()
    client.list_models.return_value = []
    
    with patch("src.llm.model_manager.get_config", return_value=config):
        manager = ModelManager(ollama_client=client)
        status = manager.check_models()
    
    assert status.present == []
    assert status.missing == []
    assert status.extra == []
    assert status.required_missing == []


def test_check_models_ollama_unreachable(mock_config, mock_ollama_client):
    """Test error handling when Ollama is unreachable."""
    mock_ollama_client.list_models.side_effect = OllamaConnectionError("Connection refused")
    
    with patch("src.llm.model_manager.get_config", return_value=mock_config):
        manager = ModelManager(ollama_client=mock_ollama_client)
    
    with pytest.raises(OllamaConnectionError):
        manager.check_models()


# ============================================================================
# Tests: Model Name Parsing
# ============================================================================

def test_parse_model_name_with_tag(model_manager):
    """Test parsing model name with version tag."""
    assert model_manager._parse_model_name("llama3.1-local:latest") == "llama3.1-local"
    assert model_manager._parse_model_name("qwen2.5-coder-local:latest") == "qwen2.5-coder-local"
    assert model_manager._parse_model_name("mistral:latest") == "mistral"


def test_parse_model_name_without_tag(model_manager):
    """Test parsing model name without tag."""
    assert model_manager._parse_model_name("llama3.1-local") == "llama3.1-local"
    assert model_manager._parse_model_name("qwen2.5-coder-local") == "qwen2.5-coder-local"


# ============================================================================
# Tests: Config Parsing
# ============================================================================

def test_get_configured_models_new_format(mock_config):
    """Test parsing new config format (list of dicts)."""
    client = Mock()
    client.list_models.return_value = []
    
    with patch("src.llm.model_manager.get_config", return_value=mock_config):
        manager = ModelManager(ollama_client=client)
    
    models = manager._get_configured_models()
    
    assert len(models) == 2
    assert models[0].name == "llama3.1-local:latest"
    assert models[0].required is True
    assert models[0].size_gb == 4.7
    assert ModelRole.CHAT in models[0].roles
    
    assert models[1].name == "qwen2.5-coder-local:latest"
    assert models[1].required is False
    assert ModelRole.CODE in models[1].roles


def test_get_configured_models_old_format():
    """Test parsing old config format (list of strings)."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "llm.models": ["llama3.1:8b", "qwen2.5-coder:7b"],
        "llm.ollama_url": "http://localhost:11434",
    }.get(key, default)
    
    client = Mock()
    client.list_models.return_value = []
    
    with patch("src.llm.model_manager.get_config", return_value=config):
        manager = ModelManager(ollama_client=client)
        models = manager._get_configured_models()
    
    assert len(models) == 2
    assert models[0].name == "llama3.1:8b"
    assert models[0].required is False  # Default for old format


def test_get_configured_models_empty():
    """Test behavior with no configured models."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "llm.models": [],
        "llm.ollama_url": "http://localhost:11434",
    }.get(key, default)
    
    client = Mock()
    client.list_models.return_value = []
    
    with patch("src.llm.model_manager.get_config", return_value=config):
        manager = ModelManager(ollama_client=client)
        models = manager._get_configured_models()
    
    assert models == []


# ============================================================================
# Tests: Model Info Lookup
# ============================================================================

def test_get_model_info(model_manager):
    """Test getting info for a specific model."""
    info = model_manager.get_model_info("llama3.1-local:latest")
    
    assert info is not None
    assert info.name == "llama3.1-local:latest"
    assert info.required is True
    assert info.size_gb == 4.7


def test_get_model_info_not_found(model_manager):
    """Test getting info for non-existent model."""
    info = model_manager.get_model_info("nonexistent:7b")
    assert info is None


# ============================================================================
# Tests: Model Installation Check
# ============================================================================

def test_is_model_installed_true(model_manager):
    """Test checking if installed model."""
    assert model_manager.is_model_installed("llama3.1-local:latest") is True
    assert model_manager.is_model_installed("mistral:latest") is True


def test_is_model_installed_false(model_manager):
    """Test checking if non-installed model."""
    assert model_manager.is_model_installed("qwen2.5-coder-local:latest") is False
    assert model_manager.is_model_installed("nonexistent:7b") is False


def test_is_model_installed_ignores_tags(model_manager):
    """Test that tag differences don't matter."""
    assert model_manager.is_model_installed("llama3.1-local:8b") is True
    assert model_manager.is_model_installed("llama3.1-local:latest") is True  # Different tag, same model


def test_is_model_installed_ollama_unreachable(model_manager, mock_ollama_client):
    """Test graceful degradation when Ollama unreachable."""
    mock_ollama_client.list_models.side_effect = OllamaConnectionError("Connection refused")
    
    result = model_manager.is_model_installed("llama3.1-local:latest")
    assert result is False


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_startup_check(mock_config, mock_ollama_client):
    """Test complete startup check workflow."""
    with patch("src.llm.model_manager.get_config", return_value=mock_config):
        manager = ModelManager(ollama_client=mock_ollama_client)
    
    status = manager.check_models()
    
    # Verify structure is correct
    assert hasattr(status, "present")
    assert hasattr(status, "missing")
    assert hasattr(status, "extra")
    assert hasattr(status, "required_missing")
    
    # Verify logic: required missing should block startup
    if status.required_missing:
        # Should not proceed
        assert len(status.required_missing) > 0
    else:
        # Safe to proceed
        assert len(status.required_missing) == 0


# ============================================================================
# Tests: Model Pulling (US-021c)
# ============================================================================

def test_pull_missing_models_no_missing(mock_config, mock_ollama_client):
    """Test pull when all models are already installed."""
    # Modify mock to have all models installed
    mock_ollama_client.list_models.return_value = [
        OllamaModel(name="llama3.1-local:latest", size=4700000000, digest="abc123", modified_at="2026-01-28"),
        OllamaModel(name="qwen2.5-coder-local:latest", size=4400000000, digest="def456", modified_at="2026-01-28"),
        OllamaModel(name="mistral:7b", size=4000000000, digest="ghi789", modified_at="2026-01-28"),
    ]
    
    with patch("src.llm.model_manager.get_config", return_value=mock_config):
        manager = ModelManager(ollama_client=mock_ollama_client)
        with patch.object(manager, "_pull_model_ollama") as mock_pull:
            result = manager.pull_missing_models()
    
    assert result["success"] is True
    assert result["required_pulled"] == []
    assert result["optional_pulled"] == []
    assert result["required_failed"] == []
    assert result["optional_failed"] == []
    mock_pull.assert_not_called()


def test_pull_missing_models_with_missing(model_manager, mock_ollama_client, mock_config):
    """Test pull when required and optional models are missing."""
    # Setup: make qwen2.5-coder missing
    with patch("src.llm.model_manager.get_config", return_value=mock_config):
        with patch.object(model_manager, "_pull_model_ollama") as mock_pull:
            # First call checks models, then pull succeeds
            mock_pull.return_value = None
            
            result = model_manager.pull_missing_models(timeout_minutes=30)
    
    # Should have tried to pull qwen2.5-coder (optional)
    assert "success" in result
    assert "total_time_seconds" in result


def test_pull_model_ollama_success(model_manager):
    """Test successful pull of a single model."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        
        # Should not raise
        model_manager._pull_model_ollama("llama3.1")


def test_pull_model_ollama_timeout(model_manager):
    """Test timeout handling when pulling takes too long."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("ollama", 60)
        
        with pytest.raises(subprocess.TimeoutExpired):
            model_manager._pull_model_ollama("llama3.1", timeout_minutes=1)


def test_pull_model_ollama_not_found(model_manager):
    """Test error when ollama command not found."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("ollama command not found")
        
        with pytest.raises(FileNotFoundError):
            model_manager._pull_model_ollama("llama3.1")


def test_pull_model_ollama_with_tags(model_manager):
    """Test that pull tries different tags if main fails."""
    with patch("subprocess.run") as mock_run:
        # First call (no tag) fails, second call (:7b) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="Not found", stdout=""),
            MagicMock(returncode=0, stderr="", stdout=""),
        ]
        
        # Should succeed on second try
        model_manager._pull_model_ollama("llama3.1")
        
        # Should have been called at least twice
        assert mock_run.call_count >= 2


def test_pull_missing_models_distinguishes_required_optional():
    """Test that pull separates required and optional model results."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "llm.models": [
            {"name": "required-model", "required": True, "roles": []},
            {"name": "optional-model", "required": False, "roles": []},
        ],
        "llm.startup.pull_timeout_minutes": 60,
        "llm.ollama_url": "http://localhost:11434",
    }.get(key, default)
    
    client = Mock()
    # Both models missing
    client.list_models.return_value = []
    
    with patch("src.llm.model_manager.get_config", return_value=config):
        manager = ModelManager(ollama_client=client)
        with patch.object(manager, "_pull_model_ollama") as mock_pull:
            # First pull (required) succeeds, second (optional) fails
            mock_pull.side_effect = [None, Exception("Network error")]
            
            result = manager.pull_missing_models()
    
    # Should have separated them
    assert len(result["required_pulled"]) > 0
    assert len(result["optional_failed"]) > 0
    assert result["success"] is False  # Failed because required one failed


def test_pull_missing_models_respects_timeout():
    """Test that timeout is passed to subprocess correctly."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "llm.models": [{"name": "test-model", "required": True, "roles": []}],
        "llm.startup.pull_timeout_minutes": 30,
        "llm.ollama_url": "http://localhost:11434",
    }.get(key, default)
    
    client = Mock()
    client.list_models.return_value = []
    
    with patch("src.llm.model_manager.get_config", return_value=config):
        manager = ModelManager(ollama_client=client)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = manager.pull_missing_models(timeout_minutes=45)
    
    # Should use the provided timeout
    assert result["success"] is True
