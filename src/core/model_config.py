"""
Model configuration validation and migration (US-021d).

This module handles:
1. Validation of llm.models section against schema
2. Automatic migration from old format (string list) to new format (dict list)
3. Default value injection for missing fields
4. Schema documentation and examples

Old format (backward compatible):
  llm:
    models:
      - "llama3.1:8b"
      - "qwen2.5-coder:7b"

New format (recommended):
  llm:
    models:
      - name: "llama3.1:8b"
        required: true
        size_gb: 4.7
        roles: ["chat", "rag"]
        description: "..."
      - name: "qwen2.5-coder:7b"
        required: false
        size_gb: 4.4
        roles: ["code"]

Design principles:
- AC-001: No hardcoded values, use ConfigManager
- AC-002: Preserve backward compatibility
- AC-003: Structured logging
- AC-004: Clear error messages with suggestions
- AC-005: Pydantic-style validation
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelConfigItem:
    """Single model configuration item (new format)."""
    name: str                          # e.g., "llama3.1:8b"
    required: bool = False             # Blocks startup if missing?
    size_gb: Optional[float] = None    # Download size (informational)
    roles: List[str] = None            # ["chat", "rag", "code"]
    description: str = ""              # User-friendly description
    
    def __post_init__(self):
        """Normalize and validate after initialization."""
        if self.roles is None:
            self.roles = []
        
        # Validate name
        if not self.name or not isinstance(self.name, str):
            raise ValueError(f"Model name must be non-empty string, got: {self.name}")
        
        # Validate roles
        valid_roles = {"chat", "rag", "code", "translation", "extraction"}
        for role in self.roles:
            if role not in valid_roles:
                logger.warning(
                    f"Unknown role '{role}' in model {self.name}. Valid: {valid_roles}"
                )


class ModelConfigValidator:
    """Validate and migrate model configuration from config.yaml."""
    
    @staticmethod
    def migrate_to_new_format(
        models_config: Union[List[str], List[Dict], List[Union[str, Dict]]]
    ) -> List[ModelConfigItem]:
        """
        Migrate models from old or mixed format to new format.
        
        Handles three cases:
        1. Old format: ["model1:tag", "model2:tag"] → converted to dicts
        2. New format: [{"name": "...", "required": true, ...}] → validated
        3. Mixed format: Both strings and dicts → both handled
        
        Args:
            models_config: Models config from yaml (can be list of str or dict)
            
        Returns:
            List of ModelConfigItem objects (new format)
            
        Raises:
            ValueError: If validation fails
        """
        if not models_config:
            logger.warning("No models configured")
            return []
        
        if not isinstance(models_config, list):
            raise ValueError(f"models must be a list, got {type(models_config).__name__}")
        
        items = []
        for idx, item in enumerate(models_config):
            try:
                if isinstance(item, str):
                    # Old format: just a model name
                    logger.debug(
                        f"Converting model {idx} from old format (string)",
                        metadata={"model": item}
                    )
                    items.append(ModelConfigItem(name=item, required=False))
                    
                elif isinstance(item, dict):
                    # New format: full config
                    config_item = ModelConfigValidator._validate_dict(item, idx)
                    items.append(config_item)
                    
                else:
                    raise ValueError(
                        f"Model {idx}: Expected string or dict, got {type(item).__name__}"
                    )
                    
            except ValueError as e:
                raise ValueError(f"Model {idx}: {str(e)}")
        
        logger.info(
            "Model configuration migrated",
            metadata={
                "total_models": len(items),
                "required": sum(1 for m in items if m.required),
                "optional": sum(1 for m in items if not m.required),
            }
        )
        
        return items
    
    @staticmethod
    def _validate_dict(item: Dict[str, Any], idx: int) -> ModelConfigItem:
        """
        Validate a single model config dict.
        
        Args:
            item: Model config dict
            idx: Index in models list (for error messages)
            
        Returns:
            ModelConfigItem
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(item, dict):
            raise ValueError(f"Expected dict, got {type(item).__name__}")
        
        # Validate required field: name
        name = item.get("name")
        if not name:
            raise ValueError("Missing required field 'name'")
        if not isinstance(name, str):
            raise ValueError(f"Field 'name' must be string, got {type(name).__name__}")
        
        # Optional fields with defaults
        required = item.get("required", False)
        if not isinstance(required, bool):
            raise ValueError(f"Field 'required' must be bool, got {type(required).__name__}")
        
        size_gb = item.get("size_gb")
        if size_gb is not None and not isinstance(size_gb, (int, float)):
            raise ValueError(f"Field 'size_gb' must be number, got {type(size_gb).__name__}")
        
        roles = item.get("roles", [])
        if not isinstance(roles, list):
            raise ValueError(f"Field 'roles' must be list, got {type(roles).__name__}")
        for role in roles:
            if not isinstance(role, str):
                raise ValueError(f"Role must be string, got {type(role).__name__}")
        
        description = item.get("description", "")
        if not isinstance(description, str):
            raise ValueError(f"Field 'description' must be string, got {type(description).__name__}")
        
        # Check for unknown fields
        known_fields = {"name", "required", "size_gb", "roles", "description"}
        unknown_fields = set(item.keys()) - known_fields
        if unknown_fields:
            logger.warning(
                f"Unknown fields in model config (will be ignored)",
                metadata={"model": name, "unknown_fields": list(unknown_fields)}
            )
        
        return ModelConfigItem(
            name=name,
            required=required,
            size_gb=size_gb,
            roles=roles,
            description=description
        )
    
    @staticmethod
    def validate_schema(models_config: Any) -> bool:
        """
        Validate that models config conforms to schema.
        
        Args:
            models_config: Raw models config from yaml
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If invalid
        """
        try:
            ModelConfigValidator.migrate_to_new_format(models_config)
            return True
        except ValueError as e:
            logger.error("Model config validation failed", metadata={"error": str(e)})
            raise
    
    @staticmethod
    def get_schema_example() -> str:
        """Get example configuration showing new format."""
        return """
# llm.models configuration (new format - recommended)
llm:
  models:
    # Required model: blocks startup if not installed
    - name: "llama3.1-local:latest"
      required: true                    # Mandatory at startup
      size_gb: 4.7                      # Storage size (informational)
      roles:                            # Model capabilities
        - "chat"                        # Good for conversation
        - "rag"                         # Good for RAG/search
      description: "General-purpose LLM for chat and RAG"
    
    # Optional model: only warned if missing
    - name: "qwen2.5-coder-local:latest"
      required: false                   # Optional at startup
      size_gb: 4.4
      roles:
        - "code"                        # Good for code tasks
      description: "Code-focused LLM"

# Old format (still supported for backward compatibility):
# llm:
#   models:
#     - "llama3.1-local:latest"
#     - "qwen2.5-coder-local:latest"
"""


def validate_model_config(models_config: Any) -> List[ModelConfigItem]:
    """
    Validate and migrate model configuration.
    
    Public entry point for validation.
    
    Args:
        models_config: Raw models config from yaml
        
    Returns:
        List of validated ModelConfigItem objects
        
    Raises:
        ValueError: If validation fails
    """
    return ModelConfigValidator.migrate_to_new_format(models_config)
