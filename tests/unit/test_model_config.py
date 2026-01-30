"""
Tests for model configuration validation and migration (US-021d).

Tests cover:
- Old format (string list) parsing
- New format (dict list) parsing
- Mixed format handling
- Schema validation
- Error handling
- Migration examples
"""

import pytest
from typing import List

from src.core.model_config import (
    ModelConfigItem,
    ModelConfigValidator,
    validate_model_config
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def old_format_models():
    """Models in old format (list of strings)."""
    return [
        "llama3.1-local:latest",
        "qwen2.5-coder-local:latest",
    ]


@pytest.fixture
def new_format_models():
    """Models in new format (list of dicts)."""
    return [
        {
            "name": "llama3.1-local:latest",
            "required": True,
            "size_gb": 4.7,
            "roles": ["chat", "rag"],
            "description": "General-purpose LLM"
        },
        {
            "name": "qwen2.5-coder-local:latest",
            "required": False,
            "size_gb": 4.4,
            "roles": ["code"],
            "description": "Code-focused LLM"
        }
    ]


@pytest.fixture
def mixed_format_models():
    """Models in mixed format (strings and dicts)."""
    return [
        "llama3.1-local:latest",  # Old format
        {
            "name": "qwen2.5-coder-local:latest",
            "required": False,
            "size_gb": 4.4,
            "roles": ["code"],
        }
    ]


# ============================================================================
# Tests: Old Format Migration
# ============================================================================

def test_migrate_old_format_single_model(old_format_models):
    """Test migrating old format (single model string)."""
    result = ModelConfigValidator.migrate_to_new_format([old_format_models[0]])
    
    assert len(result) == 1
    assert isinstance(result[0], ModelConfigItem)
    assert result[0].name == "llama3.1-local:latest"
    assert result[0].required is False  # Old format defaults to optional
    assert result[0].size_gb is None
    assert result[0].roles == []


def test_migrate_old_format_multiple_models(old_format_models):
    """Test migrating multiple models from old format."""
    result = ModelConfigValidator.migrate_to_new_format(old_format_models)
    
    assert len(result) == 2
    assert result[0].name == "llama3.1-local:latest"
    assert result[1].name == "qwen2.5-coder-local:latest"
    assert all(not m.required for m in result)  # All optional in old format


# ============================================================================
# Tests: New Format Validation
# ============================================================================

def test_validate_new_format_required(new_format_models):
    """Test validating new format with required field."""
    result = ModelConfigValidator.migrate_to_new_format(new_format_models)
    
    assert len(result) == 2
    assert result[0].required is True
    assert result[1].required is False
    assert result[0].size_gb == 4.7
    assert result[1].size_gb == 4.4


def test_validate_new_format_roles(new_format_models):
    """Test validating roles field."""
    result = ModelConfigValidator.migrate_to_new_format(new_format_models)
    
    assert result[0].roles == ["chat", "rag"]
    assert result[1].roles == ["code"]


def test_validate_new_format_description(new_format_models):
    """Test validating description field."""
    result = ModelConfigValidator.migrate_to_new_format(new_format_models)
    
    assert result[0].description == "General-purpose LLM"
    assert result[1].description == "Code-focused LLM"


# ============================================================================
# Tests: Mixed Format Handling
# ============================================================================

def test_migrate_mixed_format(mixed_format_models):
    """Test migrating mixed old and new formats."""
    result = ModelConfigValidator.migrate_to_new_format(mixed_format_models)
    
    assert len(result) == 2
    # First is migrated from string
    assert result[0].name == "llama3.1-local:latest"
    assert result[0].required is False
    # Second is validated from dict
    assert result[1].name == "qwen2.5-coder-local:latest"
    assert result[1].required is False


# ============================================================================
# Tests: Validation and Error Handling
# ============================================================================

def test_validate_missing_name():
    """Test that missing 'name' field raises error."""
    invalid_config = [
        {
            "required": True,
            "size_gb": 4.7,
        }
    ]
    
    with pytest.raises(ValueError, match="Missing required field 'name'"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_invalid_name_type():
    """Test that non-string name raises error."""
    invalid_config = [
        {
            "name": 123,  # Should be string
            "required": True,
        }
    ]
    
    with pytest.raises(ValueError, match="name' must be string"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_invalid_required_type():
    """Test that non-bool required field raises error."""
    invalid_config = [
        {
            "name": "test:latest",
            "required": "true",  # Should be bool, not string
        }
    ]
    
    with pytest.raises(ValueError, match="required' must be bool"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_invalid_size_type():
    """Test that non-numeric size_gb raises error."""
    invalid_config = [
        {
            "name": "test:latest",
            "size_gb": "4.7",  # Should be number, not string
        }
    ]
    
    with pytest.raises(ValueError, match="size_gb' must be number"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_invalid_roles_type():
    """Test that non-list roles raises error."""
    invalid_config = [
        {
            "name": "test:latest",
            "roles": "chat,rag",  # Should be list, not string
        }
    ]
    
    with pytest.raises(ValueError, match="roles' must be list"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_invalid_roles_item_type():
    """Test that non-string role items raise error."""
    invalid_config = [
        {
            "name": "test:latest",
            "roles": ["chat", 123],  # Second item should be string
        }
    ]
    
    with pytest.raises(ValueError, match="Role must be string"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_empty_config():
    """Test handling empty models config."""
    result = ModelConfigValidator.migrate_to_new_format([])
    assert result == []


def test_validate_none_config():
    """Test handling None models config."""
    result = ModelConfigValidator.migrate_to_new_format(None)
    assert result == []


def test_validate_not_list_raises_error():
    """Test that non-list config raises error."""
    invalid_config = {
        "name": "test:latest",
        "required": True,
    }
    
    with pytest.raises(ValueError, match="models must be a list"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


def test_validate_invalid_item_type():
    """Test that invalid item type raises error."""
    invalid_config = [123]  # Number instead of string or dict
    
    with pytest.raises(ValueError, match="Expected string or dict"):
        ModelConfigValidator.migrate_to_new_format(invalid_config)


# ============================================================================
# Tests: Defaults and Optional Fields
# ============================================================================

def test_defaults_required():
    """Test that 'required' defaults to False."""
    config = [{"name": "test:latest"}]
    result = ModelConfigValidator.migrate_to_new_format(config)
    
    assert result[0].required is False


def test_defaults_size_gb():
    """Test that 'size_gb' defaults to None."""
    config = [{"name": "test:latest"}]
    result = ModelConfigValidator.migrate_to_new_format(config)
    
    assert result[0].size_gb is None


def test_defaults_roles():
    """Test that 'roles' defaults to empty list."""
    config = [{"name": "test:latest"}]
    result = ModelConfigValidator.migrate_to_new_format(config)
    
    assert result[0].roles == []


def test_defaults_description():
    """Test that 'description' defaults to empty string."""
    config = [{"name": "test:latest"}]
    result = ModelConfigValidator.migrate_to_new_format(config)
    
    assert result[0].description == ""


# ============================================================================
# Tests: ModelConfigItem Initialization
# ============================================================================

def test_model_config_item_creation():
    """Test creating a ModelConfigItem."""
    item = ModelConfigItem(
        name="test:latest",
        required=True,
        size_gb=4.7,
        roles=["chat"],
        description="Test model"
    )
    
    assert item.name == "test:latest"
    assert item.required is True
    assert item.size_gb == 4.7
    assert item.roles == ["chat"]
    assert item.description == "Test model"


def test_model_config_item_empty_name_raises():
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="Model name must be non-empty string"):
        ModelConfigItem(name="")


def test_model_config_item_none_roles_defaults_to_empty_list():
    """Test that None roles becomes empty list."""
    item = ModelConfigItem(name="test:latest", roles=None)
    assert item.roles == []


# ============================================================================
# Tests: Public API
# ============================================================================

def test_validate_model_config_function(new_format_models):
    """Test public validate_model_config function."""
    result = validate_model_config(new_format_models)
    
    assert len(result) == 2
    assert all(isinstance(m, ModelConfigItem) for m in result)


def test_validate_schema_valid():
    """Test schema validation with valid config."""
    config = [{"name": "test:latest", "required": True}]
    assert ModelConfigValidator.validate_schema(config) is True


def test_validate_schema_invalid():
    """Test schema validation with invalid config."""
    config = [{"name": 123}]  # Invalid: name should be string
    
    with pytest.raises(ValueError):
        ModelConfigValidator.validate_schema(config)
