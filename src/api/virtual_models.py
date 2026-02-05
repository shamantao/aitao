"""
Virtual Model Router for AItao.

This module provides virtual model routing, allowing users to select RAG behavior
through model name suffixes. Virtual models are mapped to real Ollama models
with specific RAG configurations.

Virtual Model Suffixes:
- `-basic`: Pure LLM, no RAG context (fast response)
- `-context`: RAG enabled, considers documents and environment (slower but accurate)

Example:
    Client requests: "llama3.1-context"
    Router returns: real_model="llama3.1-local:latest", rag_enabled=True, filter=None

Configuration:
    Virtual models can be configured in config.yaml under `virtual_models` section.
    See config/config.yaml for full documentation.

Architecture Note:
    The user keeps control over context injection level through model selection,
    without needing to understand complex configuration options.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.logger import get_logger

logger = get_logger("api.virtual_models")


# ============================================================================
# Virtual Model Configuration
# ============================================================================

class RAGMode(str, Enum):
    """RAG behavior modes."""
    DISABLED = "disabled"       # No RAG context
    ENABLED = "enabled"         # RAG with optional filters
    AUTO = "auto"               # LLM decides (Sprint 7+)


@dataclass
class VirtualModelConfig:
    """Configuration for a virtual model."""
    suffix: str                                 # e.g., "basic", "context", "doc"
    rag_mode: RAGMode                           # RAG behavior
    filter_categories: Optional[List[str]]      # Category filter (None = all)
    description: str = ""                       # User-facing description


@dataclass
class ResolvedModel:
    """Result of resolving a virtual model to a real model."""
    real_model: str                             # Actual Ollama model name
    rag_enabled: bool                           # Whether RAG is enabled
    filter_categories: Optional[List[str]]      # Category filter for RAG
    is_virtual: bool                            # Was the input a virtual model?
    original_name: str                          # Original model name requested


# ============================================================================
# Default Virtual Model Mappings
# ============================================================================

# Suffix configurations (shared across all base models)
DEFAULT_SUFFIX_CONFIGS: Dict[str, VirtualModelConfig] = {
    "basic": VirtualModelConfig(
        suffix="basic",
        rag_mode=RAGMode.DISABLED,
        filter_categories=None,
        description="Fast response without context",
    ),
    "context": VirtualModelConfig(
        suffix="context",
        rag_mode=RAGMode.ENABLED,
        filter_categories=None,  # All document categories
        description="Considers your documents and environment",
    ),
}

# Base model mappings: virtual base -> real Ollama model
DEFAULT_BASE_MAPPINGS: Dict[str, str] = {
    "llama3.1": "llama3.1-local:latest",
    "qwen-coder": "qwen2.5-coder-local:latest",
    "qwen-vl": "qwen3-vl:latest",
}


# ============================================================================
# Virtual Model Router
# ============================================================================

class VirtualModelRouter:
    """
    Routes virtual model names to real Ollama models with RAG configuration.
    
    Virtual models follow the pattern: {base}-{suffix}
    Example: llama3.1-doc, qwen-coder-basic
    """
    
    def __init__(
        self,
        base_mappings: Optional[Dict[str, str]] = None,
        suffix_configs: Optional[Dict[str, VirtualModelConfig]] = None,
        use_defaults: bool = True,
    ):
        """
        Initialize the router.
        
        Args:
            base_mappings: Map of virtual base names to real model names.
            suffix_configs: Configuration for each suffix type.
            use_defaults: If True and mappings/configs are None, use defaults.
                          If False, use empty dicts (disables virtual models).
        """
        if base_mappings is not None:
            self.base_mappings = base_mappings
        elif use_defaults:
            self.base_mappings = DEFAULT_BASE_MAPPINGS.copy()
        else:
            self.base_mappings = {}
        
        if suffix_configs is not None:
            self.suffix_configs = suffix_configs
        elif use_defaults:
            self.suffix_configs = DEFAULT_SUFFIX_CONFIGS.copy()
        else:
            self.suffix_configs = {}
        
        # Build reverse mapping for listing virtual models
        self._virtual_models_cache: Optional[List[Dict]] = None
        
        logger.info(
            "VirtualModelRouter initialized",
            metadata={
                "base_models": list(self.base_mappings.keys()),
                "suffixes": list(self.suffix_configs.keys()),
            }
        )
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "VirtualModelRouter":
        """
        Create a VirtualModelRouter from config.yaml virtual_models section.
        
        Args:
            config: The virtual_models config dict from config.yaml.
                    Can be empty to use defaults.
        
        Returns:
            Configured VirtualModelRouter instance.
        
        Example config structure:
            {
                "enabled": true,
                "suffixes": {
                    "basic": {"rag_mode": "disabled", "filter_categories": null},
                    "doc": {"rag_mode": "enabled", "filter_categories": null}
                },
                "mappings": {
                    "llama3.1": "llama3.1-local:latest"
                }
            }
        """
        # Check if virtual models are disabled
        if not config.get("enabled", True):
            logger.info("Virtual models disabled in config")
            return cls(base_mappings=None, suffix_configs=None, use_defaults=False)
        
        # Parse suffix configurations
        suffix_configs: Dict[str, VirtualModelConfig] = {}
        raw_suffixes = config.get("suffixes", {})
        
        for suffix_name, suffix_data in raw_suffixes.items():
            rag_mode_str = suffix_data.get("rag_mode", "enabled")
            try:
                rag_mode = RAGMode(rag_mode_str)
            except ValueError:
                logger.warning(f"Invalid rag_mode '{rag_mode_str}' for suffix '{suffix_name}', using 'enabled'")
                rag_mode = RAGMode.ENABLED
            
            suffix_configs[suffix_name] = VirtualModelConfig(
                suffix=suffix_name,
                rag_mode=rag_mode,
                filter_categories=suffix_data.get("filter_categories"),
                description=suffix_data.get("description", ""),
            )
        
        # Use defaults if no suffixes configured
        if not suffix_configs:
            suffix_configs = DEFAULT_SUFFIX_CONFIGS.copy()
            logger.debug("Using default suffix configurations")
        
        # Parse base model mappings
        base_mappings = config.get("mappings", {})
        if not base_mappings:
            base_mappings = DEFAULT_BASE_MAPPINGS.copy()
            logger.debug("Using default base model mappings")
        
        logger.info(
            "VirtualModelRouter configured from config.yaml",
            metadata={
                "suffixes": list(suffix_configs.keys()),
                "mappings": list(base_mappings.keys()),
            }
        )
        
        return cls(base_mappings=base_mappings, suffix_configs=suffix_configs)
    
    def resolve(self, model_name: str) -> ResolvedModel:
        """
        Resolve a model name to a real model with RAG configuration.
        
        Args:
            model_name: Virtual or real model name.
            
        Returns:
            ResolvedModel with real model name and RAG config.
        """
        # Check if it's a virtual model (contains a known suffix)
        for suffix, config in self.suffix_configs.items():
            if model_name.endswith(f"-{suffix}"):
                base_name = model_name[: -(len(suffix) + 1)]  # Remove "-suffix"
                
                # Check if base is in mappings
                if base_name in self.base_mappings:
                    real_model = self.base_mappings[base_name]
                    rag_enabled = config.rag_mode in (RAGMode.ENABLED, RAGMode.AUTO)
                    
                    logger.debug(
                        "Virtual model resolved",
                        metadata={
                            "virtual": model_name,
                            "real": real_model,
                            "rag_enabled": rag_enabled,
                            "filter": config.filter_categories,
                        }
                    )
                    
                    return ResolvedModel(
                        real_model=real_model,
                        rag_enabled=rag_enabled,
                        filter_categories=config.filter_categories,
                        is_virtual=True,
                        original_name=model_name,
                    )
        
        # Not a virtual model - pass through as-is
        return ResolvedModel(
            real_model=model_name,
            rag_enabled=True,  # Default behavior
            filter_categories=None,
            is_virtual=False,
            original_name=model_name,
        )
    
    def list_virtual_models(self) -> List[Dict]:
        """
        List all available virtual models for the /v1/models endpoint.
        
        Returns:
            List of model info dicts compatible with OpenAI format.
        """
        if self._virtual_models_cache is not None:
            return self._virtual_models_cache
        
        models = []
        
        for base_name, real_model in self.base_mappings.items():
            for suffix, config in self.suffix_configs.items():
                virtual_name = f"{base_name}-{suffix}"
                models.append({
                    "id": virtual_name,
                    "object": "model",
                    "owned_by": "aitao",
                    "real_model": real_model,
                    "rag_enabled": config.rag_mode != RAGMode.DISABLED,
                    "filter_categories": config.filter_categories,
                    "description": config.description,
                })
        
        self._virtual_models_cache = models
        return models
    
    def get_all_model_ids(self) -> List[str]:
        """Get all virtual model IDs."""
        return [m["id"] for m in self.list_virtual_models()]
    
    def add_base_mapping(self, virtual_base: str, real_model: str) -> None:
        """Add or update a base model mapping."""
        self.base_mappings[virtual_base] = real_model
        self._virtual_models_cache = None  # Invalidate cache
        logger.info(f"Added base mapping: {virtual_base} -> {real_model}")
    
    def add_suffix_config(self, config: VirtualModelConfig) -> None:
        """Add or update a suffix configuration."""
        self.suffix_configs[config.suffix] = config
        self._virtual_models_cache = None  # Invalidate cache
        logger.info(f"Added suffix config: {config.suffix}")


# ============================================================================
# Module-level singleton
# ============================================================================

_router: Optional[VirtualModelRouter] = None


def get_virtual_router(config: Optional[Dict[str, Any]] = None) -> VirtualModelRouter:
    """
    Get or create the virtual model router singleton.
    
    On first call, loads configuration from config.yaml if no config is passed.
    Subsequent calls return the cached instance.
    
    Args:
        config: Optional virtual_models config dict. If None, loads from config.yaml.
        
    Returns:
        VirtualModelRouter instance.
    """
    global _router
    if _router is None:
        if config is None:
            # Load from config.yaml
            config = _load_config_from_yaml()
        _router = VirtualModelRouter.from_config(config)
    return _router


def _load_config_from_yaml() -> Dict[str, Any]:
    """Load virtual_models section from config.yaml."""
    try:
        from src.core.config import get_config
        cfg = get_config()
        vm_config = cfg.get_section("virtual_models")
        if vm_config:
            logger.debug("Loaded virtual_models config from config.yaml")
            return vm_config
    except Exception as e:
        logger.warning(f"Could not load virtual_models from config.yaml: {e}")
    
    # Return empty dict to use defaults
    return {}


def reset_router() -> None:
    """Reset the router singleton (useful for testing)."""
    global _router
    _router = None
    logger.debug("Virtual model router reset")


def resolve_model(model_name: str) -> ResolvedModel:
    """Convenience function to resolve a model name."""
    return get_virtual_router().resolve(model_name)
