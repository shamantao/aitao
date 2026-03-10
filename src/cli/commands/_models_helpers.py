"""
Helper functions for model management CLI commands.

This module provides utilities for:
- Model name validation and normalization
- Config file reading/writing
- Interactive prompts for model metadata
- Config validation with pydantic

Used by: src/cli/commands/models.py (US-021e)
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

import typer
try:
    import tomllib                    # Python 3.11+ stdlib
except ModuleNotFoundError:
    import tomli as tomllib           # uv pip install tomli

try:
    import tomli_w                    # uv pip install tomli-w
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "tomli-w is required for writing TOML config. "
        "Install it with: uv pip install tomli-w"
    ) from exc

from rich.console import Console
from rich.prompt import Prompt, Confirm

from core.config import get_config
from core.logger import get_logger
from core.pathmanager import AitaoPathManager

logger = get_logger(__name__)
console = Console()


def validate_model_name(model_name: str) -> str:
    """
    Validate and normalize model name.
    
    Accepts:
    - "llama3.1" (default tag: latest)
    - "llama3.1:8b" (explicit tag)
    - "mistral:latest"
    
    Rejects:
    - Empty string
    - Invalid characters (@#$%)
    - Names without alphanumeric characters
    
    Args:
        model_name: Raw model name input
    
    Returns:
        Normalized model name with tag (e.g., "llama3.1:latest")
    
    Raises:
        typer.BadParameter: If validation fails
    """
    if not model_name or not model_name.strip():
        raise typer.BadParameter("Model name cannot be empty")
    
    model_name = model_name.strip()
    
    # Check for invalid characters
    invalid_chars = set("@#$%^&*(){}[]|\\<>?,")
    if any(c in model_name for c in invalid_chars):
        raise typer.BadParameter(
            f"Model name contains invalid characters: {', '.join(invalid_chars)}"
        )
    
    # Add default tag if missing
    if ":" not in model_name:
        model_name = f"{model_name}:latest"
    
    logger.debug(
        "Model name validated",
        metadata={"original": model_name.split(":")[0], "normalized": model_name}
    )
    
    return model_name


def get_model_from_config(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Find model in config by name (handles variants with/without tag).
    
    Args:
        model_name: Model name (e.g., "llama3.1:8b")
    
    Returns:
        Model dict from config.toml or None if not found
    """
    config = get_config()
    models = config.get("llm.models", [])
    
    # Extract base name (without tag) for comparison
    base_name = model_name.split(":")[0]
    
    for model in models:
        if isinstance(model, dict):
            configured_base = model.get("name", "").split(":")[0]
            if configured_base == base_name:
                return model
        elif isinstance(model, str):
            # Legacy format (just string)
            configured_base = model.split(":")[0]
            if configured_base == base_name:
                return {"name": model, "required": False, "roles": []}
    
    return None


def load_config_yaml() -> Dict[str, Any]:
    """
    Load config.toml into memory for modification.

    Returns:
        Parsed config dict

    Raises:
        FileNotFoundError: If config.toml doesn't exist
        ConfigError: If TOML syntax is invalid
    """
    pathman = AitaoPathManager()
    config_path = pathman.config_path  # Use attribute, not method

    if not config_path.exists():
        raise FileNotFoundError(f"config.toml not found at {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    logger.debug(
        "Config loaded",
        metadata={"path": str(config_path), "sections": list(config.keys())}
    )

    return config


def save_config_yaml(config: Dict[str, Any]) -> bool:
    """
    Safely write updated config back to config.toml.

    Args:
        config: Updated config dict

    Returns:
        True if successful

    Raises:
        PermissionError: If cannot write to config.toml
        ValueError: If config is not serialisable to TOML
    """
    pathman = AitaoPathManager()
    config_path = pathman.config_path  # Use attribute, not method

    # Validate by round-tripping before writing
    try:
        test_bytes = tomli_w.dumps(config)
        tomllib.loads(test_bytes)
    except Exception as e:
        logger.error(
            "Config validation failed before save",
            metadata={"error": str(e)}
        )
        raise

    # Write to file
    try:
        with open(config_path, "wb") as f:
            tomli_w.dump(config, f)

        logger.info(
            "Config saved successfully",
            metadata={"path": str(config_path)}
        )
        return True
    except PermissionError as e:
        logger.error(
            "Permission denied writing config",
            metadata={"path": str(config_path), "error": str(e)}
        )
        raise
    except Exception as e:
        logger.error(
            "Error writing config",
            metadata={"path": str(config_path), "error": str(e)}
        )
        raise


def prompt_model_metadata() -> Dict[str, Any]:
    """
    Interactive prompt for model role and required flag.
    
    Returns:
        Dict with keys:
        - role: List[str] (e.g., ["rag", "code"])
        - required: bool
    """
    console.print()
    
    # Role selection (allow multiple)
    valid_roles = ["rag", "code", "extraction", "chat"]
    roles_input = Prompt.ask(
        "Model roles (comma-separated from: rag, code, extraction, chat)",
        default="rag"
    )
    
    roles = [r.strip() for r in roles_input.split(",") if r.strip()]
    # Validate roles
    invalid_roles = [r for r in roles if r not in valid_roles]
    if invalid_roles:
        console.print(f"[yellow]⚠ Invalid roles: {', '.join(invalid_roles)}[/yellow]")
        console.print(f"[dim]Valid roles: {', '.join(valid_roles)}[/dim]")
        roles = ["rag"]  # Default fallback
    
    # Required flag
    required = Confirm.ask("Mark as required for startup?", default=False)
    
    logger.debug(
        "Model metadata collected",
        metadata={"roles": roles, "required": required}
    )
    
    return {"role": roles, "required": required}


def check_model_dependencies(model_name: str, operation: str = "remove") -> Dict[str, Any]:
    """
    Check if removing a model would break system.
    
    Warns if:
    - It's the only model with its role(s)
    - It's marked required
    
    Args:
        model_name: Model to check
        operation: "remove" or "modify"
    
    Returns:
        Dict with keys:
        - has_warnings: bool
        - only_model_for_roles: List[str]
        - is_required: bool
    """
    model = get_model_from_config(model_name)
    if not model:
        return {
            "has_warnings": False,
            "only_model_for_roles": [],
            "is_required": False
        }
    
    config = get_config()
    all_models = config.get("llm.models", [])
    model_roles = model.get("roles", [])
    is_required = model.get("required", False)
    
    # Check if only model for each role
    only_model_for_roles = []
    for role in model_roles:
        count_with_role = sum(
            1 for m in all_models
            if role in m.get("roles", [])
        )
        if count_with_role == 1:
            only_model_for_roles.append(role)
    
    has_warnings = bool(only_model_for_roles) or is_required
    
    return {
        "has_warnings": has_warnings,
        "only_model_for_roles": only_model_for_roles,
        "is_required": is_required
    }


def get_model_info_for_display(model: Dict[str, Any]) -> Dict[str, str]:
    """
    Format model info for display in tables.
    
    Args:
        model: Model dict from config
    
    Returns:
        Dict with display-friendly strings
    """
    return {
        "name": model.get("name", "?"),
        "size": f"{model.get('size_gb', '?')}G",
        "roles": ", ".join(model.get("roles", [])),
        "required": "✓" if model.get("required") else "○",
        "description": model.get("description", "")
    }
