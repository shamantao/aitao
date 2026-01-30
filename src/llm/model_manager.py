"""
ModelManager: Manage Ollama model lifecycle.

This module handles:
1. Model verification: Check which configured models are installed in Ollama
2. Model status reporting: Present/missing/extra models
3. Error reporting: Clear messages when models are missing
4. Future phases: Automatic downloading (US-021c)

Responsibilities:
- Verify models configured in config.yaml exist in Ollama
- Parse Ollama's `ollama list` output
- Report detailed status (required missing, optional missing, extra)
- Integration point for startup checks and CLI commands

Architecture:
- Depends on: OllamaClient (for model listing), ConfigManager
- Used by: lifecycle.py (startup checks), CLI commands
- Canonical structure: ModelStatus (in registry.py)

Design Principles:
- AC-001: Use get_config() to access configuration
- AC-002: No hardcoded paths
- AC-003: Structured logging only (no print)
- AC-004: No placeholder functions
- AC-005: Use ModelInfo/ModelStatus from registry.py
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import logging

from src.core.config import get_config
from src.core.logger import get_logger
from src.core.registry import ModelStatus, ModelInfo, ModelRole, ConfigKeys
from src.llm.ollama_client import OllamaClient, OllamaConnectionError


logger = get_logger(__name__)


class ModelManager:
    """
    Manage Ollama model lifecycle.
    
    Primary use cases:
    1. Startup: check_models() → verify all required models exist
    2. CLI: models status → show current state
    3. Future: pull_missing_models() → download models (US-021c)
    
    Usage:
        manager = ModelManager()
        status = manager.check_models()
        
        if status.required_missing:
            print(f"ERROR: Missing required models: {status.required_missing}")
            sys.exit(1)
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize ModelManager.
        
        Args:
            ollama_client: OllamaClient instance (creates new one if not provided).
                          Useful for testing with mock clients.
        """
        config = get_config()
        ollama_url = config.get("llm.ollama_url") or config.get(ConfigKeys.OLLAMA_HOST)
        
        if ollama_client:
            self.ollama = ollama_client
        else:
            self.ollama = OllamaClient(config=config, logger=logger)
        
        self.config = config
        logger.info("ModelManager initialized", metadata={"ollama_url": ollama_url})
    
    def check_models(self) -> ModelStatus:
        """
        Check status of configured models.
        
        Compares models listed in config.yaml against Ollama's available models.
        
        Returns:
            ModelStatus with present/missing/extra models
            
        Side effects:
            Logs model status at INFO level
            Logs warnings for required missing models
            
        Raises:
            OllamaConnectionError: If cannot connect to Ollama
        """
        logger.info("Checking model status...")
        
        # Get configured models from config.yaml
        configured_models = self._get_configured_models()
        
        # Get installed models from Ollama
        try:
            installed_models = self._get_installed_models()
        except OllamaConnectionError as e:
            logger.error("Cannot connect to Ollama", metadata={"error": str(e)})
            raise
        
        # Parse model names (ignore tags like ":latest")
        configured_names = {self._parse_model_name(m.name) for m in configured_models}
        installed_names = {self._parse_model_name(m) for m in installed_models}
        
        # Categorize
        present = sorted(list(configured_names & installed_names))
        missing = sorted(list(configured_names - installed_names))
        extra = sorted(list(installed_names - configured_names))
        
        # Find required models that are missing
        configured_map = {m.name: m for m in configured_models}
        required_missing = [
            name for name in missing
            if any(
                self._parse_model_name(m.name) == name and m.required
                for m in configured_models
            )
        ]
        
        # Log results
        logger.info(
            "Model check complete",
            metadata={
                "present_count": len(present),
                "missing_count": len(missing),
                "extra_count": len(extra),
                "required_missing_count": len(required_missing)
            }
        )
        
        if present:
            logger.info("Present models", metadata={"models": present})
        if missing:
            logger.warning("Missing models", metadata={"models": missing})
        if extra:
            logger.info("Extra models (not configured)", metadata={"models": extra})
        if required_missing:
            logger.error("Required models missing", metadata={"models": required_missing})
        
        return ModelStatus(
            present=present,
            missing=missing,
            extra=extra,
            required_missing=required_missing
        )
    
    def _get_configured_models(self) -> List[ModelInfo]:
        """
        Parse models from config.yaml.
        
        Returns list of ModelInfo objects from llm.models config.
        Handles both old format (simple list of strings) and new format (list of dicts).
        
        Returns:
            List of ModelInfo objects
        """
        config = get_config()
        models_config = config.get(ConfigKeys.LLM_MODELS, [])
        
        if not models_config:
            logger.warning("No models configured in config.yaml")
            return []
        
        models = []
        for item in models_config:
            if isinstance(item, str):
                # Old format: simple string "llama3.1:8b"
                models.append(ModelInfo(name=item, required=False))
            elif isinstance(item, dict):
                # New format: dict with name, required, roles, etc.
                models.append(ModelInfo(
                    name=item.get("name", ""),
                    required=item.get("required", False),
                    size_gb=item.get("size_gb"),
                    roles=[ModelRole(r) for r in item.get("roles", [])],
                    description=item.get("description", "")
                ))
            else:
                logger.warning("Invalid model config format", item=item)
        
        return models
    
    def _get_installed_models(self) -> List[str]:
        """
        Get list of installed models from Ollama.
        
        Returns:
            List of model names (e.g., ["llama3.1:8b", "qwen2.5-coder:7b"])
            
        Raises:
            OllamaConnectionError: If cannot connect to Ollama
        """
        try:
            models = self.ollama.list_models()
            model_names = [m.name for m in models]
            return model_names
        except OllamaConnectionError as e:
            logger.error("Failed to get installed models from Ollama", metadata={"error": str(e)})
            raise
    
    def _parse_model_name(self, full_name: str) -> str:
        """
        Parse model name (remove version tag if present).
        
        Examples:
            "llama3.1:8b" → "llama3.1"
            "qwen2.5-coder:7b" → "qwen2.5-coder"
            "qwen2-vl" → "qwen2-vl"
        
        Args:
            full_name: Model name with optional tag
            
        Returns:
            Model name without tag
        """
        return full_name.split(":")[0]
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get detailed info for a specific model.
        
        Args:
            model_name: Model name (e.g., "llama3.1:8b")
            
        Returns:
            ModelInfo if found, None otherwise
        """
        configured = self._get_configured_models()
        for model in configured:
            if self._parse_model_name(model.name) == self._parse_model_name(model_name):
                return model
        return None
    
    def is_model_installed(self, model_name: str) -> bool:
        """
        Check if a specific model is installed.
        
        Args:
            model_name: Model name to check
            
        Returns:
            True if installed, False otherwise
        """
        try:
            installed = self._get_installed_models()
            parsed_search = self._parse_model_name(model_name)
            return any(self._parse_model_name(m) == parsed_search for m in installed)
        except OllamaConnectionError:
            logger.error("Cannot check if model installed - Ollama unreachable", metadata={"model": model_name})
            return False
