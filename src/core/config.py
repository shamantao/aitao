"""
AiTao — src/core/config.py

Layered TOML config loader, aligned with tao-init v1.0.0 python adapter.
Replaces the former YAML-based loader (migrated US-045, 2026-03-10).

Uses tomllib (Python 3.11+ stdlib). No external dependencies required.
For Python 3.10, tomli is used as a fallback (must be installed).

Layer priority (highest wins):
  config/config.toml  →  ~/.config/aitao/user.toml  →  env vars (APP__SECTION__KEY)

Usage:
    from src.core.config import ConfigManager

    config = ConfigManager()
    storage_root = config.get("paths.storage_root")
    port         = config.get("api.port", 8200)
    indexing     = config.get_section("indexing")
    config.reload()
"""

from __future__ import annotations

import copy
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib                  # Python 3.11+ stdlib
except ModuleNotFoundError:
    try:
        import tomli as tomllib     # uv pip install tomli (Python 3.10 fallback)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "tomllib not available. "
            "Python 3.11+ includes it in stdlib. "
            "For Python 3.10, run: uv pip install tomli"
        ) from exc

try:
    from src.core.logger import get_logger
except ImportError:
    from core.logger import get_logger


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge `override` into `base`.
    Returns the mutated `base`. Does not affect scalar types.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """
    Thread-safe layered TOML configuration manager.

    Layers (later overrides earlier):
      1. Built-in defaults (_DEFAULTS)
      2. config/config.toml  (project config, committed)
      3. ~/.config/aitao/user.toml  (user overrides, not committed)
      4. Environment variables:  APP__<SECTION>__<KEY>=value

    Public API:
      get(key, default)     — dot-notation key, e.g. "paths.storage_root"
      get_section(section)  — returns full section dict (copy)
      require(key)          — like get() but raises SystemExit if missing
      set(key, value)       — runtime override (not persisted)
      reload()              — reload from disk
      dump()                — full merged config (for debugging)
    """

    _DEFAULTS: dict[str, Any] = {
        "app": {
            "name": "aitao",
            "mode": "normal",
            "version": "2.5.1",
        },
        "paths": {
            "storage_root": "${HOME}/.aitao/data",
            "models_dir":   "${HOME}/.aitao/models",
        },
        "indexing": {
            "enabled":          True,
            "interval_minutes": 60,
            "include_paths":    [],
            "exclude_dirs":     [".git", ".DS_Store", "__pycache__"],
            "exclude_files":    [],
            "exclude_extensions": [],
        },
        "ocr": {
            "provider":             "auto",
            "languages":            ["fr", "en"],
            "confidence_threshold": 0.7,
        },
        "translation": {
            "provider":    "mbart50",
            "source_lang": "fr",
            "target_lang": "zh_TW",
        },
        "search": {
            "meilisearch": {
                "url":        "http://localhost:7700",
                "api_key":    "",
                "index_name": "aitao_documents",
            },
            "lancedb": {
                "embedding_model": "BAAI/bge-m3",
                "table_name":      "aitao_embeddings",
                "dimension":       1024,
                "top_k":           20,
                "min_score":       0.45,
            },
        },
        "api": {
            "host": "127.0.0.1",
            "port": 8200,
        },
        "resources": {
            "max_workers": 4,
            "batch_size":  10,
        },
        "logger": {
            "level":          "info",
            "console_pretty": True,
            "file_json":      True,
            "max_file_mb":    100,
            "max_files":      5,
        },
        "rag": {
            "enabled":             True,
            "use_chunks":          True,
            "max_context_chunks":  5,
            "context_max_tokens":  4000,
            "min_relevance_score": 0.3,
        },
    }

    def __init__(self, config_path: Optional[str] = None, auto_reload: bool = False):
        """
        Initialize ConfigManager.

        Args:
            config_path:  Path to config.toml. If None, searches standard locations.
            auto_reload:  Reserved for future hot-reload support.
        """
        self.logger = get_logger("config")
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._last_modified: Optional[float] = None
        self._auto_reload = auto_reload

        # Resolve config file path
        if config_path:
            # Accept both old .yaml and new .toml paths transparently during migration
            resolved = Path(config_path)
            if not resolved.exists() and resolved.suffix in (".yaml", ".yml"):
                toml_equivalent = resolved.with_suffix(".toml")
                if toml_equivalent.exists():
                    resolved = toml_equivalent
            self.config_path = resolved
        else:
            self.config_path = self._find_config()

        self.reload()
        self.logger.info(
            "ConfigManager initialized",
            metadata={"config_path": str(self.config_path), "sections": list(self._data.keys())},
        )

    # ------------------------------------------------------------------
    def _find_project_root(self) -> Optional[Path]:
        """Walk up from this file searching for project markers."""
        current = Path(__file__).resolve().parent
        markers = ["aitao.sh", "pyproject.toml"]
        for _ in range(10):
            for marker in markers:
                if (current / marker).exists():
                    return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    def _find_config(self) -> Path:
        """Locate config.toml in standard locations."""
        project_root = self._find_project_root()
        candidates: list[Path] = []

        if project_root:
            candidates += [
                project_root / "config" / "config.toml",
                project_root / "config.toml",
            ]
        candidates += [
            Path("config/config.toml"),
            Path("config.toml"),
            Path.home() / ".config" / "aitao" / "user.toml",
        ]

        for path in candidates:
            if path.exists():
                return path

        raise ConfigError(
            f"Configuration file not found. Searched: {[str(p) for p in candidates]}\n"
            "Run: cp config/config.toml.template config/config.toml"
        )

    # ------------------------------------------------------------------
    def reload(self) -> None:
        """
        Reload configuration from disk.
        Thread-safe; can be called manually to pick up file changes.
        """
        with self._lock:
            try:
                if not self.config_path.exists():
                    raise ConfigError(f"Config file not found: {self.config_path}")

                current_mtime = self.config_path.stat().st_mtime
                if self._last_modified and current_mtime == self._last_modified:
                    return

                # 1. Start from defaults
                merged: dict[str, Any] = copy.deepcopy(self._DEFAULTS)

                # 2. Load project config
                with open(self.config_path, "rb") as f:
                    file_data = tomllib.load(f)
                _deep_merge(merged, file_data)

                # 3. Load optional user overrides (~/.config/aitao/user.toml)
                user_toml = Path.home() / ".config" / "aitao" / "user.toml"
                if user_toml.exists():
                    with open(user_toml, "rb") as f:
                        _deep_merge(merged, tomllib.load(f))

                # 4. Apply env var overrides: APP__SECTION__KEY=value
                for envvar, value in os.environ.items():
                    if envvar.startswith("APP__"):
                        parts = envvar.split("__", 2)
                        if len(parts) == 3:
                            _, section, key = parts
                            section = section.lower()
                            key = key.lower()
                            merged.setdefault(section, {})[key] = value

                # 5. Expand ${HOME} and ${storage_root}  
                self._data = self._expand_vars(merged)
                self._last_modified = current_mtime

            except (OSError, ValueError) as e:
                raise ConfigError(f"Invalid TOML syntax: {e}") from e

    # ------------------------------------------------------------------
    def _expand_vars(self, data: Any) -> Any:
        """Recursively expand ${HOME} and ${storage_root} in string values."""
        if isinstance(data, dict):
            # Resolve storage_root first so it can be referenced in other values
            storage_root = data.get("paths", {}).get("storage_root", "")
            if storage_root:
                storage_root = os.path.expandvars(storage_root.replace("${HOME}", str(Path.home())))

            result = {}
            for k, v in data.items():
                result[k] = self._expand_vars(v)
            # Second pass to resolve ${storage_root} which may appear in sub-sections
            if storage_root:
                result = self._replace_storage_root(result, storage_root)
            return result
        elif isinstance(data, list):
            return [self._expand_vars(item) for item in data]
        elif isinstance(data, str):
            return os.path.expandvars(data.replace("${HOME}", str(Path.home())))
        return data

    def _replace_storage_root(self, data: Any, storage_root: str) -> Any:
        """Replace ${storage_root} after storage_root itself is resolved."""
        if isinstance(data, dict):
            return {k: self._replace_storage_root(v, storage_root) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_storage_root(item, storage_root) for item in data]
        elif isinstance(data, str) and "${storage_root}" in data:
            return data.replace("${storage_root}", storage_root)
        return data

    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        """
        Return a config value by dot-notation key.

        Examples:
            config.get("paths.storage_root")
            config.get("api.port", 8200)
            config.get("llm.generation.temperature", 0.7)
        """
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts:
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return default
            return node

    def require(self, key: str) -> Any:
        """Like get() but raises SystemExit with a clear message if the key is missing."""
        _sentinel = object()
        value = self.get(key, _sentinel)
        if value is _sentinel:
            raise SystemExit(f"Required config key missing: {key}")
        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Return an entire top-level section as a dict (copy)."""
        with self._lock:
            if section not in self._data:
                raise ConfigError(f"Configuration section not found: '{section}'")
            return dict(self._data[section])

    def set(self, key: str, value: Any) -> None:
        """
        Set a config value at runtime (not persisted to disk).
        Supports dot-notation: config.set("api.port", 9000)
        """
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

    def dump(self) -> dict[str, Any]:
        """Return the full merged config dict (useful for debugging)."""
        with self._lock:
            return copy.deepcopy(self._data)


# ---------------------------------------------------------------------------
# Singleton helper (backward-compatible with existing callers)
# ---------------------------------------------------------------------------

_config_manager: Optional[ConfigManager] = None
_singleton_lock = threading.Lock()


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """
    Return a process-wide ConfigManager singleton.

    Args:
        config_path: Path to config.toml (only used on first call).

    Returns:
        Shared ConfigManager instance.
    """
    global _config_manager
    with _singleton_lock:
        if _config_manager is None:
            _config_manager = ConfigManager(config_path)
        return _config_manager

