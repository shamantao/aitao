from typing import Dict, List, Any
from pathlib import Path
import os
from src.core.lib.path_manager import GenericPathManager

class AitaoPathManager(GenericPathManager):
    """
    Project-specific PathManager for 'Aitao'.
    Inherits generic capabilities and implements specific business logic.
    """

    def __init__(self):
        # 1. Initialize logic specifying markers unique to this project
        super().__init__(
            config_filename="config.yaml",
            root_markers=["aitao.sh", "requirements.txt"] 
        )
        
        # 2. Define default paths (fallback logic)
        self.system_paths = {
            "storage_root": self._ensure_path("data"),
            "models_dir": self.root.parent / "AI-models",
            "logs_dir": self._ensure_path("data/logs")
        }
        
        # 3. Apply specific configuration logic
        self._apply_aitao_config()

    def _ensure_path(self, relative_path: str) -> Path:
        """Helper to get a path relative to project root."""
        return self.root / relative_path

    def _apply_aitao_config(self):
        """
        Reads loaded configuration and updates specific system paths.
        Implements the logic for variable substitution (${HOME}, ${storage_root}, etc).
        """
        # --- Storage Root (resolved first, no dependencies) ---
        raw_storage = self.get_config_value("paths", "storage_root")
        if raw_storage:
            self.system_paths["storage_root"] = self.resolve_path(raw_storage)
        
        # --- Models Dir (resolved first, no dependencies) ---
        raw_models = self.get_config_value("paths", "models_dir")
        if raw_models:
            self.system_paths["models_dir"] = self.resolve_path(raw_models)

        # --- Logs Dir (with substitution of $storage_root) ---
        raw_logs = self.get_config_value("paths", "logs_dir")
        if raw_logs:
            # Context contains the already-resolved storage_root value
            context = {
                "storage_root": str(self.system_paths["storage_root"])
            }
            p = self.resolve_path(raw_logs, context_vars=context)
            
            # If after resolution it is still relative, anchor it to storage_root
            if not p.is_absolute():
                self.system_paths["logs_dir"] = self.system_paths["storage_root"] / p
            else:
                self.system_paths["logs_dir"] = p
        else:
            # Default: logs inside storage_root
            self.system_paths["logs_dir"] = self.system_paths["storage_root"] / "logs"

        # 4. Create Directory Structure
        self._create_structure()

    def _create_structure(self):
        """Creates the required folder hierarchy for AItao V2."""
        storage = self.system_paths["storage_root"]
        storage.mkdir(parents=True, exist_ok=True)
        
        # V2 structure
        (storage / "lancedb").mkdir(exist_ok=True)
        (storage / "queue").mkdir(exist_ok=True)
        (storage / "cache").mkdir(exist_ok=True)
        (storage / "cache" / "ocr").mkdir(exist_ok=True)
        (storage / "cache" / "translations").mkdir(exist_ok=True)
        (storage / "corrections").mkdir(exist_ok=True)
        
        # Legacy (keep for now)
        (storage / "history").mkdir(exist_ok=True)
        
        self.system_paths["logs_dir"].mkdir(parents=True, exist_ok=True)

    # --- Project Specific Accessors ---

    def get_storage_root(self) -> Path:
        return self.system_paths["storage_root"]

    def get_logs_dir(self) -> Path:
        return self.system_paths["logs_dir"]

    def get_vector_db_path(self) -> Path:
        return self.system_paths["storage_root"] / "lancedb"

    def get_sql_db_path(self) -> str:
        db_path = self.system_paths["storage_root"] / "history" / "chat_history.db"
        return str(db_path)

    def get_models_dir(self) -> Path:
        return self.system_paths["models_dir"]

    def get_queue_dir(self) -> Path:
        """Get queue directory for task management."""
        return self.system_paths["storage_root"] / "queue"

    def get_queue_file(self) -> Path:
        """Get path to the task queue JSON file."""
        return self.get_queue_dir() / "tasks.json"

    def get_scanner_state_file(self) -> Path:
        """Get path to scanner state file for incremental scans."""
        return self.system_paths["storage_root"] / "scanner_state.json"

    def get_cache_dir(self, cache_type: str = None) -> Path:
        """
        Get cache directory.
        
        Args:
            cache_type: Optional subdirectory ('ocr', 'translations'). 
                       If None, returns base cache dir.
        
        Returns:
            Path to cache directory
        """
        base_cache = self.system_paths["storage_root"] / "cache"
        if cache_type:
            return base_cache / cache_type
        return base_cache

    def get_corrections_dir(self) -> Path:
        """Get corrections directory for user feedback."""
        return self.system_paths["storage_root"] / "corrections"

    def get_indexing_config(self) -> Dict[str, List[str]]:
        """Specific logic to parse indexing arrays."""
        idx = self.config.get("indexing", {})
        raw_includes = idx.get("include_paths", [])
        
        # Validate existence of included paths
        resolved_includes = [str(self.resolve_path(p)) for p in raw_includes if self.resolve_path(p).exists()]
        
        return {
            "include_paths": resolved_includes,
            "exclude_dirs": idx.get("exclude_dirs", []),
            "exclude_files": idx.get("exclude_files", []),
            "exclude_extensions": idx.get("exclude_extensions", [])
        }

    def get_ocr_config(self) -> Dict[str, Any]:
        """Return OCR router configuration with defaults."""
        ocr_cfg = self.config.get("ocr", {})
        qwen_path = ocr_cfg.get("qwen_model_path", "")
        if qwen_path:
            qwen_path = str(self.resolve_path(qwen_path))
        return {
            "engine": ocr_cfg.get("engine", "auto"),
            "table_area_min": float(ocr_cfg.get("table_area_min", 0.15)),
            "min_intersections": int(ocr_cfg.get("min_intersections", 4)),
            "min_line_density": float(ocr_cfg.get("min_line_density", 0.0005)),
            "qwen_model_path": qwen_path,
        }

# Global Instance
path_manager = AitaoPathManager()
