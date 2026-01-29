"""
Configuration manager for AItao V2.

This module provides centralized configuration loading and validation:
- Loads config.yaml with schema validation
- Provides default values for missing keys
- Hot-reload on file modification
- Environment variable substitution
- Nested key access with dot notation
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
from threading import Lock

try:
    from src.core.logger import get_logger
except ImportError:
    from core.logger import get_logger


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigManager:
    """
    Centralized configuration manager with validation and hot-reload.
    
    Features:
    - Loads YAML configuration files
    - Validates required sections
    - Provides default values
    - Monitors file changes for hot-reload
    - Thread-safe access
    - Environment variable expansion
    
    Usage:
        config = ConfigManager("config/config.yaml")
        storage_root = config.get("paths.storage_root")
        indexing = config.get_section("indexing")
        config.reload()  # Manual reload
    """
    
    # Default configuration schema
    DEFAULTS = {
        "paths": {
            "storage_root": "${HOME}/.aitao/data",
            "models_dir": "${HOME}/.aitao/models",
        },
        "indexing": {
            "enabled": True,
            "interval_minutes": 60,
            "include_paths": [],
            "exclude_patterns": [".git", ".DS_Store", "__pycache__"],
        },
        "ocr": {
            "provider": "paddleocr",
            "languages": ["fr", "en"],
            "confidence_threshold": 0.7,
        },
        "translation": {
            "provider": "mbart50",
            "source_lang": "fr",
            "target_lang": "zh_TW",
        },
        "search": {
            "meilisearch": {
                "url": "http://localhost:7700",
                "api_key": "",
            },
            "lancedb": {
                "embedding_model": "BAAI/bge-m3",
            },
        },
        "api": {
            "host": "127.0.0.1",
            "port": 8200,
        },
        "resources": {
            "max_workers": 4,
            "batch_size": 10,
        },
        "logging": {
            "level": "INFO",
            "max_file_size_mb": 100,
            "backup_count": 5,
        },
    }
    
    def __init__(self, config_path: Optional[str] = None, auto_reload: bool = False):
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Path to config.yaml file. If None, searches in standard locations.
            auto_reload: Enable automatic reload on file changes (not implemented yet)
        
        Raises:
            ConfigError: If config file not found or invalid
        """
        self.logger = get_logger("config")
        self._lock = Lock()
        self._config: Dict[str, Any] = {}
        self._last_modified: Optional[float] = None
        self._auto_reload = auto_reload
        
        # Determine config file path
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Search in standard locations
            search_paths = [
                Path("config/config.yaml"),
                Path("config/config.yml"),
                Path("config.yaml"),
                Path.home() / ".aitao" / "config.yaml",
            ]
            
            self.config_path = None
            for path in search_paths:
                if path.exists():
                    self.config_path = path
                    break
            
            if not self.config_path:
                raise ConfigError(
                    f"Configuration file not found. Searched: {[str(p) for p in search_paths]}"
                )
        
        # Load configuration
        self.reload()
        
        self.logger.info(
            "ConfigManager initialized",
            metadata={
                "config_path": str(self.config_path),
                "sections": list(self._config.keys())
            }
        )
    
    def reload(self) -> None:
        """
        Reload configuration from file.
        
        This method is thread-safe and can be called manually to refresh config.
        
        Raises:
            ConfigError: If reload fails
        """
        with self._lock:
            try:
                if not self.config_path.exists():
                    raise ConfigError(f"Config file not found: {self.config_path}")
                
                # Check if file was modified
                current_mtime = self.config_path.stat().st_mtime
                if self._last_modified and current_mtime == self._last_modified:
                    self.logger.debug("Config file unchanged, skipping reload")
                    return
                
                # Load YAML
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f)
                
                if not isinstance(raw_config, dict):
                    raise ConfigError("Config file must contain a YAML dictionary")
                
                # Validate required sections BEFORE merging defaults
                self._validate_raw_config(raw_config)
                
                # Merge with defaults
                self._config = self._merge_with_defaults(raw_config)
                
                # Expand environment variables ($HOME, $USER, etc.)
                self._config = self._expand_env_vars(self._config)
                
                # Expand internal variables (${storage_root}, etc.)
                self._config = self._expand_internal_vars(self._config)
                
                # Validate final config
                self._validate_config()
                
                self._last_modified = current_mtime
                
                self.logger.info(
                    "Configuration reloaded",
                    metadata={
                        "modified": datetime.fromtimestamp(current_mtime).isoformat(),
                        "sections": list(self._config.keys())
                    }
                )
                
            except yaml.YAMLError as e:
                raise ConfigError(f"Invalid YAML syntax: {e}")
            except Exception as e:
                raise ConfigError(f"Failed to reload config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Supports dot notation for nested keys: "paths.storage_root"
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        
        Example:
            >>> config.get("paths.storage_root")
            "/Users/phil/.aitao/data"
            >>> config.get("api.port", 8200)
            8200
        """
        with self._lock:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name (e.g., "indexing", "ocr", "api")
        
        Returns:
            Dictionary of section configuration
        
        Raises:
            ConfigError: If section doesn't exist
        
        Example:
            >>> indexing = config.get_section("indexing")
            >>> print(indexing["enabled"])
            True
        """
        with self._lock:
            if section not in self._config:
                raise ConfigError(f"Configuration section not found: {section}")
            
            return self._config[section].copy()
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value at runtime (not persisted to file).
        
        Args:
            key: Configuration key (supports dot notation)
            value: New value
        
        Example:
            >>> config.set("api.port", 8201)
        """
        with self._lock:
            keys = key.split('.')
            target = self._config
            
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            
            target[keys[-1]] = value
            
            self.logger.debug(
                "Configuration value updated",
                metadata={"key": key, "value": value}
            )
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge loaded config with defaults."""
        result = self.DEFAULTS.copy()
        
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = {**result[key], **value}
            else:
                result[key] = value
        
        return result
    
    def _expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively expand environment variables in config values."""
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(item) for item in config]
        elif isinstance(config, str):
            return os.path.expandvars(config)
        else:
            return config

    def _expand_internal_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand internal config variables like ${storage_root}.
        
        These are variables defined within the config file itself,
        not shell environment variables.
        """
        # First, resolve the storage_root (it may contain $HOME)
        storage_root = config.get("paths", {}).get("storage_root", "")
        if storage_root:
            storage_root = os.path.expandvars(storage_root)
            storage_root = os.path.expanduser(storage_root)
        
        def replace_vars(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: replace_vars(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_vars(item) for item in value]
            elif isinstance(value, str):
                # Replace ${storage_root} with the resolved value
                if "${storage_root}" in value:
                    return value.replace("${storage_root}", storage_root)
                return value
            else:
                return value
        
        return replace_vars(config)
    
    def _validate_raw_config(self, config: Dict[str, Any]) -> None:
        """
        Validate raw configuration before merging defaults.
        
        Raises:
            ConfigError: If validation fails
        """
        required_sections = ["paths"]
        
        for section in required_sections:
            if section not in config:
                raise ConfigError(f"Missing required section: {section}")
    
    def _validate_config(self) -> None:
        """
        Validate configuration has required sections.
        
        Raises:
            ConfigError: If validation fails
        """
        required_sections = ["paths"]
        
        for section in required_sections:
            if section not in self._config:
                raise ConfigError(f"Missing required section: {section}")


# Global singleton instance
_config_manager: Optional[ConfigManager] = None
_config_lock = Lock()


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """
    Get global ConfigManager instance (singleton pattern).
    
    Args:
        config_path: Path to config file (only used on first call)
    
    Returns:
        Global ConfigManager instance
    
    Example:
        >>> config = get_config()
        >>> port = config.get("api.port")
    """
    global _config_manager
    
    with _config_lock:
        if _config_manager is None:
            _config_manager = ConfigManager(config_path)
        
        return _config_manager
