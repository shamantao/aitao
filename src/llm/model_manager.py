"""
ModelManager: Manage Ollama model lifecycle.

This module handles:
1. Model verification: Check which configured models are installed in Ollama
2. Model status reporting: Present/missing/extra models
3. Error reporting: Clear messages when models are missing
4. Future phases: Automatic downloading (US-021c)

Responsibilities:
- Verify models configured in config.toml exist in Ollama
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
from typing import List, Optional, Dict, Any, Callable
import logging
import subprocess
import asyncio

from src.core.config import get_config
from src.core.logger import get_logger
from src.core.registry import ModelStatus, ModelInfo, ModelRole, ConfigKeys
from src.core.model_config import validate_model_config, ModelConfigItem
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
        
        Compares models listed in config.toml against Ollama's available models.
        
        Returns:
            ModelStatus with present/missing/extra models
            
        Side effects:
            Logs model status at INFO level
            Logs warnings for required missing models
            
        Raises:
            OllamaConnectionError: If cannot connect to Ollama
        """
        logger.info("Checking model status...")
        
        # Get configured models from config.toml
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
        Parse models from config.toml with validation.
        
        Uses ModelConfigValidator to:
        1. Validate schema (required fields, types)
        2. Migrate old format to new format
        3. Inject defaults for optional fields
        
        Returns list of ModelInfo objects from llm.models config.
        Handles both old format (simple list of strings) and new format (list of dicts).
        
        Returns:
            List of ModelInfo objects
            
        Raises:
            ValueError: If configuration is invalid
        """
        config = get_config()
        models_config = config.get(ConfigKeys.LLM_MODELS, [])
        
        if not models_config:
            logger.warning("No models configured in config.toml")
            return []
        
        try:
            # Validate and migrate to new format
            validated_items = validate_model_config(models_config)
        except ValueError as e:
            logger.error(
                f"Invalid model configuration: {str(e)}",
                metadata={"error": str(e)}
            )
            raise
        
        # Convert validated items to ModelInfo objects
        models = []
        for item in validated_items:
            models.append(ModelInfo(
                name=item.name,
                required=item.required,
                size_gb=item.size_gb,
                roles=[ModelRole(r) if r in [role.value for role in ModelRole] else r 
                       for r in item.roles],
                description=item.description
            ))
        
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
    
    def pull_missing_models(
        self,
        timeout_minutes: Optional[int] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Download all missing required and optional models from Ollama hub.
        
        Uses 'ollama pull <model>' for each missing model.
        
        Args:
            timeout_minutes: Maximum time to wait (per model or total?).
                           Reads from config.toml → llm.startup.pull_timeout_minutes if None.
            progress_callback: Optional callback called with (model_name, percent_complete).
                             Useful for CLI progress display.
        
        Returns:
            Dict with:
            {
                "success": bool,           # True if all required models downloaded
                "required_pulled": [...],  # Required models successfully pulled
                "required_failed": [...],  # Required models that failed
                "optional_pulled": [...],  # Optional models successfully pulled
                "optional_failed": [...],  # Optional models that failed
                "total_time_seconds": float
            }
        
        Raises:
            OllamaConnectionError: If Ollama is unreachable
        
        Side effects:
            Logs progress at INFO/WARNING/ERROR levels
        """
        import time
        start_time = time.time()
        
        # Get config
        config = get_config()
        if timeout_minutes is None:
            timeout_minutes = config.get("llm.startup.pull_timeout_minutes") or 60
        
        logger.info(
            "Starting model pull",
            metadata={"timeout_minutes": timeout_minutes}
        )
        
        # Check current status
        try:
            status = self.check_models()
        except OllamaConnectionError as e:
            logger.error("Cannot check models - Ollama unreachable", metadata={"error": str(e)})
            return {
                "success": False,
                "required_pulled": [],
                "required_failed": [],
                "optional_pulled": [],
                "optional_failed": [],
                "error": str(e),
                "total_time_seconds": time.time() - start_time
            }
        
        # Get configured models for metadata
        configured = self._get_configured_models()
        configured_map = {m.name: m for m in configured}
        
        # Separate required and optional missing models
        required_missing = []
        optional_missing = []
        
        for model_name in status.missing:
            # Find model metadata
            model_info = None
            for m in configured:
                if self._parse_model_name(m.name) == model_name:
                    model_info = m
                    break
            
            if model_info and model_info.required:
                required_missing.append(model_name)
            else:
                optional_missing.append(model_name)
        
        if not required_missing and not optional_missing:
            logger.info("All configured models are already installed")
            return {
                "success": True,
                "required_pulled": [],
                "required_failed": [],
                "optional_pulled": [],
                "optional_failed": [],
                "total_time_seconds": time.time() - start_time
            }
        
        # Prepare to pull
        to_pull = required_missing + optional_missing
        results = {
            "success": True,
            "required_pulled": [],
            "required_failed": [],
            "optional_pulled": [],
            "optional_failed": [],
        }
        
        logger.info(
            "Models to pull",
            metadata={
                "required": required_missing,
                "optional": optional_missing,
                "total": len(to_pull)
            }
        )
        
        # Pull each model
        for idx, model_name in enumerate(to_pull):
            is_required = model_name in required_missing
            
            # Report progress
            percent = (idx / len(to_pull)) * 100 if to_pull else 0
            if progress_callback:
                progress_callback(model_name, percent)
            
            logger.info(f"Pulling {'required' if is_required else 'optional'} model",
                       metadata={"model": model_name, "index": idx + 1, "total": len(to_pull)})
            
            # Try to pull with ollama pull
            try:
                self._pull_model_ollama(model_name, timeout_minutes=timeout_minutes)
                
                logger.info("Successfully pulled model", metadata={"model": model_name})
                if is_required:
                    results["required_pulled"].append(model_name)
                else:
                    results["optional_pulled"].append(model_name)
                    
            except subprocess.TimeoutExpired:
                msg = f"Timeout pulling {model_name} (limit: {timeout_minutes}min)"
                logger.error(msg, metadata={"model": model_name})
                results["success"] = False
                if is_required:
                    results["required_failed"].append(model_name)
                else:
                    results["optional_failed"].append(model_name)
                    
            except Exception as e:
                logger.error(
                    f"Failed to pull model: {str(e)}",
                    metadata={"model": model_name, "error": str(e)}
                )
                results["success"] = False
                if is_required:
                    results["required_failed"].append(model_name)
                else:
                    results["optional_failed"].append(model_name)
        
        # Final report
        results["total_time_seconds"] = time.time() - start_time
        
        logger.info(
            "Pull operation complete",
            metadata={
                "success": results["success"],
                "required_pulled": len(results["required_pulled"]),
                "required_failed": len(results["required_failed"]),
                "optional_pulled": len(results["optional_pulled"]),
                "optional_failed": len(results["optional_failed"]),
                "total_seconds": results["total_time_seconds"]
            }
        )
        
        return results
    
    def _pull_model_ollama(self, model_name: str, timeout_minutes: int = 60) -> None:
        """
        Pull a single model using 'ollama pull' command.
        
        Args:
            model_name: Model name (e.g., "llama3.1")
            timeout_minutes: Max time to wait
            
        Raises:
            subprocess.TimeoutExpired: If pull takes too long
            subprocess.CalledProcessError: If ollama pull fails
            FileNotFoundError: If ollama command not found
        """
        timeout_seconds = timeout_minutes * 60
        
        # Try to pull with most common tags
        # First try without tag, then common variants
        tags_to_try = [
            "",           # ollama pull llama3.1
            ":7b",        # ollama pull llama3.1:7b
            ":8b",        # ollama pull llama3.1:8b
        ]
        
        last_error = None
        for tag in tags_to_try:
            try:
                full_model_name = f"{model_name}{tag}" if tag else model_name
                logger.debug(f"Attempting to pull {full_model_name}")
                
                # Use subprocess to run 'ollama pull'
                result = subprocess.run(
                    ["ollama", "pull", full_model_name],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully pulled {full_model_name}")
                    return
                else:
                    last_error = result.stderr or result.stdout or "Unknown error"
                    logger.debug(f"ollama pull {full_model_name} failed: {last_error}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout pulling {model_name}{tag}")
                raise
            except FileNotFoundError:
                raise FileNotFoundError("'ollama' command not found. Is Ollama installed?")
            except subprocess.CalledProcessError as e:
                last_error = e.stderr or e.stdout or str(e)
                logger.debug(f"CalledProcessError for {model_name}{tag}: {last_error}")
        
        # If we get here, all tags failed
        raise Exception(f"Failed to pull {model_name}: {last_error or 'Unknown error'}")
