"""
Unit tests for Virtual Model Router.

Tests the virtual model routing functionality that allows users to control
RAG behavior through model name suffixes.
"""

import pytest
from src.api.virtual_models import (
    VirtualModelRouter,
    VirtualModelConfig,
    ResolvedModel,
    RAGMode,
    resolve_model,
    get_virtual_router,
    reset_router,
    DEFAULT_BASE_MAPPINGS,
    DEFAULT_SUFFIX_CONFIGS,
)


class TestRAGMode:
    """Tests for RAGMode enum."""
    
    def test_rag_mode_values(self):
        """Test RAGMode enum has expected values."""
        assert RAGMode.DISABLED == "disabled"
        assert RAGMode.ENABLED == "enabled"
        assert RAGMode.AUTO == "auto"


class TestVirtualModelConfig:
    """Tests for VirtualModelConfig dataclass."""
    
    def test_config_creation(self):
        """Test creating a virtual model config."""
        config = VirtualModelConfig(
            suffix="test",
            rag_mode=RAGMode.ENABLED,
            filter_categories=["code"],
            description="Test config",
        )
        assert config.suffix == "test"
        assert config.rag_mode == RAGMode.ENABLED
        assert config.filter_categories == ["code"]
        assert config.description == "Test config"
    
    def test_config_no_filter(self):
        """Test config with no category filter."""
        config = VirtualModelConfig(
            suffix="doc",
            rag_mode=RAGMode.ENABLED,
            filter_categories=None,
        )
        assert config.filter_categories is None


class TestResolvedModel:
    """Tests for ResolvedModel dataclass."""
    
    def test_resolved_virtual(self):
        """Test resolved model from virtual name."""
        resolved = ResolvedModel(
            real_model="llama3.1-local:latest",
            rag_enabled=True,
            filter_categories=None,
            is_virtual=True,
            original_name="llama3.1-doc",
        )
        assert resolved.is_virtual
        assert resolved.real_model == "llama3.1-local:latest"
        assert resolved.original_name == "llama3.1-doc"
    
    def test_resolved_real(self):
        """Test resolved model from real name."""
        resolved = ResolvedModel(
            real_model="qwen2.5-coder:7b",
            rag_enabled=True,
            filter_categories=None,
            is_virtual=False,
            original_name="qwen2.5-coder:7b",
        )
        assert not resolved.is_virtual
        assert resolved.real_model == resolved.original_name


class TestDefaultConfigs:
    """Tests for default configurations."""
    
    def test_default_base_mappings_exist(self):
        """Test default base mappings are defined."""
        assert "llama3.1" in DEFAULT_BASE_MAPPINGS
        assert "qwen-coder" in DEFAULT_BASE_MAPPINGS
        assert "qwen-vl" in DEFAULT_BASE_MAPPINGS
    
    def test_default_suffix_configs_exist(self):
        """Test default suffix configs are defined."""
        assert "basic" in DEFAULT_SUFFIX_CONFIGS
        assert "context" in DEFAULT_SUFFIX_CONFIGS
        # Only 2 suffixes now (US-029b): basic and context
        assert len(DEFAULT_SUFFIX_CONFIGS) == 2
    
    def test_basic_suffix_disables_rag(self):
        """Test -basic suffix disables RAG."""
        config = DEFAULT_SUFFIX_CONFIGS["basic"]
        assert config.rag_mode == RAGMode.DISABLED
    
    def test_context_suffix_enables_full_rag(self):
        """Test -context suffix enables full RAG."""
        config = DEFAULT_SUFFIX_CONFIGS["context"]
        assert config.rag_mode == RAGMode.ENABLED
        assert config.filter_categories is None  # All categories (US-029b)


class TestVirtualModelRouter:
    """Tests for VirtualModelRouter class."""
    
    @pytest.fixture
    def router(self):
        """Create a fresh router for testing."""
        return VirtualModelRouter()
    
    def test_router_initialization(self, router):
        """Test router initializes with defaults."""
        assert router.base_mappings == DEFAULT_BASE_MAPPINGS
        assert router.suffix_configs == DEFAULT_SUFFIX_CONFIGS
    
    def test_resolve_virtual_basic(self, router):
        """Test resolving a -basic virtual model."""
        resolved = router.resolve("llama3.1-basic")
        
        assert resolved.is_virtual
        assert resolved.real_model == "llama3.1-local:latest"
        assert resolved.rag_enabled is False
        assert resolved.filter_categories is None
        assert resolved.original_name == "llama3.1-basic"
    
    def test_resolve_virtual_context(self, router):
        """Test resolving a -context virtual model."""
        resolved = router.resolve("llama3.1-context")
        
        assert resolved.is_virtual
        assert resolved.real_model == "llama3.1-local:latest"
        assert resolved.rag_enabled is True
        assert resolved.filter_categories is None  # All categories (US-029b)
    
    def test_resolve_real_model_passthrough(self, router):
        """Test resolving a real model passes through."""
        resolved = router.resolve("qwen2.5-coder:7b")
        
        assert not resolved.is_virtual
        assert resolved.real_model == "qwen2.5-coder:7b"
        assert resolved.rag_enabled is True  # Default behavior
        assert resolved.original_name == "qwen2.5-coder:7b"
    
    def test_resolve_unknown_base_passthrough(self, router):
        """Test resolving unknown base with suffix passes through."""
        resolved = router.resolve("unknown-basic")
        
        # "unknown" is not in base_mappings, so treat as real model
        assert not resolved.is_virtual
        assert resolved.real_model == "unknown-basic"
    
    def test_resolve_qwen_vl(self, router):
        """Test resolving qwen-vl virtual models."""
        resolved = router.resolve("qwen-vl-context")
        
        assert resolved.is_virtual
        assert resolved.real_model == "qwen3-vl:latest"
        assert resolved.rag_enabled is True
    
    def test_list_virtual_models(self, router):
        """Test listing all virtual models."""
        models = router.list_virtual_models()
        
        # Should have base_count * suffix_count models
        expected_count = len(DEFAULT_BASE_MAPPINGS) * len(DEFAULT_SUFFIX_CONFIGS)
        assert len(models) == expected_count
        
        # Check structure
        first_model = models[0]
        assert "id" in first_model
        assert "object" in first_model
        assert "owned_by" in first_model
        assert "real_model" in first_model
        assert "rag_enabled" in first_model
    
    def test_list_virtual_models_caching(self, router):
        """Test virtual models list is cached."""
        models1 = router.list_virtual_models()
        models2 = router.list_virtual_models()
        
        assert models1 is models2  # Same object (cached)
    
    def test_get_all_model_ids(self, router):
        """Test getting all virtual model IDs."""
        ids = router.get_all_model_ids()
        
        assert "llama3.1-basic" in ids
        assert "llama3.1-context" in ids
        assert "qwen-coder-basic" in ids
        assert "qwen-vl-context" in ids
    
    def test_add_base_mapping(self, router):
        """Test adding a new base mapping."""
        router.add_base_mapping("mistral", "mistral:7b")
        
        resolved = router.resolve("mistral-context")
        assert resolved.is_virtual
        assert resolved.real_model == "mistral:7b"
    
    def test_add_base_mapping_invalidates_cache(self, router):
        """Test adding mapping invalidates cache."""
        models1 = router.list_virtual_models()
        router.add_base_mapping("mistral", "mistral:7b")
        models2 = router.list_virtual_models()
        
        assert models1 is not models2  # Cache invalidated
    
    def test_add_suffix_config(self, router):
        """Test adding a new suffix config."""
        new_config = VirtualModelConfig(
            suffix="custom",
            rag_mode=RAGMode.ENABLED,
            filter_categories=["test"],
            description="Custom suffix",
        )
        router.add_suffix_config(new_config)
        
        resolved = router.resolve("llama3.1-custom")
        assert resolved.is_virtual
        assert resolved.filter_categories == ["test"]


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_resolve_model_function(self):
        """Test resolve_model convenience function."""
        resolved = resolve_model("llama3.1-context")
        
        assert resolved.is_virtual
        assert resolved.real_model == "llama3.1-local:latest"
    
    def test_get_virtual_router_singleton(self):
        """Test get_virtual_router returns singleton."""
        router1 = get_virtual_router()
        router2 = get_virtual_router()
        
        assert router1 is router2


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def router(self):
        """Create a fresh router for testing."""
        return VirtualModelRouter()
    
    def test_empty_model_name(self, router):
        """Test empty model name passes through."""
        resolved = router.resolve("")
        
        assert not resolved.is_virtual
        assert resolved.real_model == ""
    
    def test_suffix_only_model_name(self, router):
        """Test model name that is just a suffix."""
        resolved = router.resolve("-basic")
        
        # "-basic" with empty base won't match
        assert not resolved.is_virtual
    
    def test_model_with_colon_tag(self, router):
        """Test model names with tags pass through correctly."""
        resolved = router.resolve("llama3.1:8b")
        
        assert not resolved.is_virtual
        assert resolved.real_model == "llama3.1:8b"
    
    def test_custom_router(self):
        """Test router with custom configs."""
        custom_base = {"mymodel": "my-model:latest"}
        custom_suffix = {
            "fast": VirtualModelConfig(
                suffix="fast",
                rag_mode=RAGMode.DISABLED,
                filter_categories=None,
            )
        }
        
        router = VirtualModelRouter(
            base_mappings=custom_base,
            suffix_configs=custom_suffix,
        )
        
        resolved = router.resolve("mymodel-fast")
        assert resolved.is_virtual
        assert resolved.real_model == "my-model:latest"
        assert resolved.rag_enabled is False


class TestFromConfig:
    """Tests for VirtualModelRouter.from_config factory method."""
    
    def test_from_empty_config_uses_defaults(self):
        """Test empty config uses default mappings and suffixes."""
        router = VirtualModelRouter.from_config({})
        
        assert router.base_mappings == DEFAULT_BASE_MAPPINGS
        assert router.suffix_configs == DEFAULT_SUFFIX_CONFIGS
    
    def test_from_config_disabled(self):
        """Test disabled virtual models creates empty router."""
        config = {"enabled": False}
        router = VirtualModelRouter.from_config(config)
        
        assert router.base_mappings == {}
        assert router.suffix_configs == {}
    
    def test_from_config_custom_mappings(self):
        """Test config with custom base mappings."""
        config = {
            "enabled": True,
            "mappings": {
                "mymodel": "my-model:latest",
                "other": "other-model:7b",
            },
        }
        router = VirtualModelRouter.from_config(config)
        
        assert "mymodel" in router.base_mappings
        assert router.base_mappings["mymodel"] == "my-model:latest"
        # Suffixes default since not specified
        assert router.suffix_configs == DEFAULT_SUFFIX_CONFIGS
    
    def test_from_config_custom_suffixes(self):
        """Test config with custom suffix definitions."""
        config = {
            "enabled": True,
            "suffixes": {
                "fast": {
                    "rag_mode": "disabled",
                    "filter_categories": None,
                    "description": "Fast mode",
                },
                "full": {
                    "rag_mode": "enabled",
                    "filter_categories": ["all"],
                    "description": "Full RAG",
                },
            },
        }
        router = VirtualModelRouter.from_config(config)
        
        assert "fast" in router.suffix_configs
        assert router.suffix_configs["fast"].rag_mode == RAGMode.DISABLED
        assert "full" in router.suffix_configs
        assert router.suffix_configs["full"].rag_mode == RAGMode.ENABLED
        # Base mappings default since not specified
        assert router.base_mappings == DEFAULT_BASE_MAPPINGS
    
    def test_from_config_full_custom(self):
        """Test config with both custom mappings and suffixes."""
        config = {
            "enabled": True,
            "mappings": {
                "llama": "llama3.1:latest",
            },
            "suffixes": {
                "norag": {
                    "rag_mode": "disabled",
                    "filter_categories": None,
                },
            },
        }
        router = VirtualModelRouter.from_config(config)
        
        resolved = router.resolve("llama-norag")
        assert resolved.is_virtual
        assert resolved.real_model == "llama3.1:latest"
        assert resolved.rag_enabled is False
    
    def test_from_config_invalid_rag_mode_fallback(self):
        """Test invalid rag_mode falls back to enabled."""
        config = {
            "suffixes": {
                "test": {
                    "rag_mode": "invalid_mode",
                    "filter_categories": None,
                },
            },
        }
        router = VirtualModelRouter.from_config(config)
        
        assert router.suffix_configs["test"].rag_mode == RAGMode.ENABLED
    
    def test_from_config_auto_rag_mode(self):
        """Test auto rag_mode is parsed correctly."""
        config = {
            "suffixes": {
                "auto": {
                    "rag_mode": "auto",
                    "filter_categories": None,
                    "description": "Auto mode",
                },
            },
        }
        router = VirtualModelRouter.from_config(config)
        
        assert router.suffix_configs["auto"].rag_mode == RAGMode.AUTO
    
    def test_from_config_filter_categories_list(self):
        """Test filter_categories as list is parsed correctly."""
        config = {
            "suffixes": {
                "code": {
                    "rag_mode": "enabled",
                    "filter_categories": ["code", "config", "tech"],
                },
            },
        }
        router = VirtualModelRouter.from_config(config)
        
        assert router.suffix_configs["code"].filter_categories == ["code", "config", "tech"]


class TestResetRouter:
    """Tests for reset_router function."""
    
    def test_reset_router_clears_singleton(self):
        """Test reset_router clears the cached instance."""
        router1 = get_virtual_router()
        reset_router()
        router2 = get_virtual_router()
        
        # Should be different instances after reset
        assert router1 is not router2
