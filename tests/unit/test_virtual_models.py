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
        assert "doc" in DEFAULT_SUFFIX_CONFIGS
        assert "smart" in DEFAULT_SUFFIX_CONFIGS
    
    def test_basic_suffix_disables_rag(self):
        """Test -basic suffix disables RAG."""
        config = DEFAULT_SUFFIX_CONFIGS["basic"]
        assert config.rag_mode == RAGMode.DISABLED
    
    def test_doc_suffix_enables_full_rag(self):
        """Test -doc suffix enables full RAG."""
        config = DEFAULT_SUFFIX_CONFIGS["doc"]
        assert config.rag_mode == RAGMode.ENABLED
        assert config.filter_categories is None  # All categories
    
    def test_context_suffix_filters_categories(self):
        """Test -context suffix filters to code categories."""
        config = DEFAULT_SUFFIX_CONFIGS["context"]
        assert config.rag_mode == RAGMode.ENABLED
        assert "code" in config.filter_categories


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
    
    def test_resolve_virtual_doc(self, router):
        """Test resolving a -doc virtual model."""
        resolved = router.resolve("llama3.1-doc")
        
        assert resolved.is_virtual
        assert resolved.real_model == "llama3.1-local:latest"
        assert resolved.rag_enabled is True
        assert resolved.filter_categories is None
    
    def test_resolve_virtual_context(self, router):
        """Test resolving a -context virtual model."""
        resolved = router.resolve("qwen-coder-context")
        
        assert resolved.is_virtual
        assert resolved.real_model == "qwen2.5-coder-local:latest"
        assert resolved.rag_enabled is True
        assert resolved.filter_categories == ["code", "config"]
    
    def test_resolve_virtual_smart(self, router):
        """Test resolving a -smart virtual model."""
        resolved = router.resolve("llama3.1-smart")
        
        assert resolved.is_virtual
        assert resolved.rag_enabled is True  # AUTO mode enables RAG
    
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
        resolved = router.resolve("qwen-vl-doc")
        
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
        assert "llama3.1-doc" in ids
        assert "qwen-coder-context" in ids
        assert "qwen-vl-smart" in ids
    
    def test_add_base_mapping(self, router):
        """Test adding a new base mapping."""
        router.add_base_mapping("mistral", "mistral:7b")
        
        resolved = router.resolve("mistral-doc")
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
        resolved = resolve_model("llama3.1-doc")
        
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
