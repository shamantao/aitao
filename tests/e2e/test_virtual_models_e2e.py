"""
E2E Tests for Virtual Model Routing.

These tests validate the complete virtual model routing workflow:
1. Virtual model names are correctly resolved to real Ollama models
2. RAG behavior is correctly controlled by suffixes
3. /v1/models endpoint lists virtual models
4. Unknown models are handled gracefully

Run with: pytest tests/e2e/test_virtual_models_e2e.py -v
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.virtual_models import (
    VirtualModelRouter,
    ResolvedModel,
    RAGMode,
    resolve_model,
    get_virtual_router,
    reset_router,
)
from core.config import get_config


class TestVirtualModelRoutingE2E:
    """E2E tests for virtual model routing from config.toml."""
    
    @pytest.fixture(autouse=True)
    def reset_router_before_test(self):
        """Reset router singleton before each test."""
        reset_router()
        yield
        reset_router()
    
    def test_router_loads_from_config_yaml(self):
        """Router should load configuration from config.toml."""
        router = get_virtual_router()
        
        # Should have base mappings from config
        assert len(router.base_mappings) > 0
        assert "llama3.1" in router.base_mappings or len(router.base_mappings) >= 1
        
        # Should have suffix configs
        assert len(router.suffix_configs) > 0
    
    def test_config_yaml_virtual_models_section(self):
        """config.toml should have virtual_models section."""
        config = get_config()
        vm_config = config.get_section("virtual_models")
        
        assert vm_config is not None
        assert "enabled" in vm_config
        assert "suffixes" in vm_config
        assert "mappings" in vm_config
    
    def test_qwen_coder_basic_no_rag(self):
        """qwen-coder-basic should resolve with RAG disabled."""
        resolved = resolve_model("qwen-coder-basic")
        
        assert resolved.is_virtual is True
        assert resolved.real_model == "qwen2.5-coder-local:latest"
        assert resolved.rag_enabled is False
        assert resolved.original_name == "qwen-coder-basic"
    
    def test_qwen_coder_context_filtered_rag(self):
        """qwen-coder-context should resolve with filtered RAG."""
        resolved = resolve_model("qwen-coder-context")
        
        assert resolved.is_virtual is True
        assert resolved.real_model == "qwen2.5-coder-local:latest"
        assert resolved.rag_enabled is True
        assert resolved.filter_categories is not None
        assert "code" in resolved.filter_categories
    
    def test_llama31_doc_full_rag(self):
        """llama3.1-doc should resolve with full RAG (no filter)."""
        resolved = resolve_model("llama3.1-doc")
        
        assert resolved.is_virtual is True
        assert resolved.real_model == "llama3.1-local:latest"
        assert resolved.rag_enabled is True
        assert resolved.filter_categories is None  # All categories
    
    def test_qwen_vl_basic(self):
        """qwen-vl-basic should resolve to qwen3-vl with no RAG."""
        resolved = resolve_model("qwen-vl-basic")
        
        assert resolved.is_virtual is True
        assert resolved.real_model == "qwen3-vl:latest"
        assert resolved.rag_enabled is False
    
    def test_unknown_model_passthrough(self):
        """Unknown model names should pass through as-is."""
        resolved = resolve_model("some-unknown-model:7b")
        
        assert resolved.is_virtual is False
        assert resolved.real_model == "some-unknown-model:7b"
        assert resolved.original_name == "some-unknown-model:7b"
    
    def test_real_ollama_model_passthrough(self):
        """Real Ollama model names should pass through."""
        resolved = resolve_model("llama3.1-local:latest")
        
        assert resolved.is_virtual is False
        assert resolved.real_model == "llama3.1-local:latest"


class TestVirtualModelsEndpoint:
    """E2E tests for /v1/models endpoint with virtual models."""
    
    @pytest.fixture(autouse=True)
    def reset_router_before_test(self):
        """Reset router singleton before each test."""
        reset_router()
        yield
        reset_router()
    
    def test_list_virtual_models(self):
        """Should list all virtual models."""
        router = get_virtual_router()
        models = router.list_virtual_models()
        
        # Should have base_count * suffix_count models
        assert len(models) > 0
        
        # Check structure
        model_ids = [m["id"] for m in models]
        assert "llama3.1-basic" in model_ids
        assert "llama3.1-doc" in model_ids
        assert "qwen-coder-basic" in model_ids
        assert "qwen-vl-doc" in model_ids
    
    def test_virtual_model_info_structure(self):
        """Virtual model info should have correct structure."""
        router = get_virtual_router()
        models = router.list_virtual_models()
        
        for model in models:
            assert "id" in model
            assert "object" in model
            assert "owned_by" in model
            assert "real_model" in model
            assert "rag_enabled" in model
            assert model["object"] == "model"
            assert model["owned_by"] == "aitao"


class TestRAGBehaviorWithVirtualModels:
    """E2E tests for RAG behavior controlled by virtual model suffixes."""
    
    @pytest.fixture(autouse=True)
    def reset_router_before_test(self):
        """Reset router singleton before each test."""
        reset_router()
        yield
        reset_router()
    
    def test_basic_suffix_disables_rag_context(self):
        """With -basic suffix, no RAG context should be injected."""
        resolved = resolve_model("llama3.1-basic")
        
        # When rag_enabled is False, chat endpoint should NOT call RAG
        assert resolved.rag_enabled is False
        
        # This would be used in chat.py:
        # if resolved.is_virtual:
        #     effective_rag = resolved.rag_enabled  # False for -basic
        # -> No RAG context injection
    
    def test_context_suffix_filters_rag(self):
        """With -context suffix, RAG should filter to code categories."""
        resolved = resolve_model("qwen-coder-context")
        
        assert resolved.rag_enabled is True
        assert resolved.filter_categories == ["code", "config"]
        
        # This would be used in chat.py:
        # filters = {"category": resolved.filter_categories}
        # -> Only code/config documents retrieved
    
    def test_doc_suffix_full_rag(self):
        """With -doc suffix, full RAG with all documents."""
        resolved = resolve_model("llama3.1-doc")
        
        assert resolved.rag_enabled is True
        assert resolved.filter_categories is None
        
        # This would be used in chat.py:
        # filters = None  # All categories
        # -> All documents available for RAG
    
    def test_smart_suffix_auto_mode(self):
        """With -smart suffix, RAG mode is AUTO."""
        router = get_virtual_router()
        config = router.suffix_configs.get("smart")
        
        assert config is not None
        assert config.rag_mode == RAGMode.AUTO
        
        # In future Sprint 7+, AUTO mode will let LLM decide
        resolved = resolve_model("llama3.1-smart")
        assert resolved.rag_enabled is True  # Currently treated as enabled


class TestConfigurationOverrides:
    """E2E tests for configuration overrides."""
    
    def test_custom_router_with_different_mappings(self):
        """Custom router can have different base mappings."""
        custom_mappings = {
            "mistral": "mistral:7b-instruct",
            "phi": "phi3:medium",
        }
        
        router = VirtualModelRouter(base_mappings=custom_mappings)
        
        resolved = router.resolve("mistral-doc")
        assert resolved.is_virtual is True
        assert resolved.real_model == "mistral:7b-instruct"
        
        resolved = router.resolve("phi-basic")
        assert resolved.is_virtual is True
        assert resolved.real_model == "phi3:medium"
        assert resolved.rag_enabled is False
    
    def test_disabled_router(self):
        """Disabled router passes all models through."""
        router = VirtualModelRouter.from_config({"enabled": False})
        
        # With empty mappings, nothing resolves as virtual
        resolved = router.resolve("llama3.1-doc")
        assert resolved.is_virtual is False
        assert resolved.real_model == "llama3.1-doc"
