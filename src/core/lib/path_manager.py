import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# Gestion des imports TOML : Ordre de priorité (Standard > Tomli > Toml externe)
tomllib = None
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        try:
            import toml as tomllib # Fallback sur la lib 'toml' classique souvent présente
        except ImportError:
            tomllib = None

# YAML support for V2
yaml = None
try:
    import yaml
except ImportError:
    pass

class GenericPathManager:
    """
    A generic, reusable configuration and path manager.
    
    Features:
    - Root project detection based on marker files.
    - TOML configuration loading.
    - Variable substitution (e.g., $storage_root, $HOME or ~/).
    - API Route construction (protocol, host, port).
    """

    def __init__(self, 
                 config_filename: str = "config.toml", 
                 root_markers: List[str] = None,
                 base_dir: str = None):
        """
        Initialize the PathManager.
        
        :param config_filename: Name of the config file to load.
        :param root_markers: List of files/dirs to look for to identify project root (e.g. ['.git', 'pyproject.toml']).
        :param base_dir: Optional explicit root path. If None, auto-detection starts from this file's location.
        """
        self.config_filename = config_filename
        self.root_markers = root_markers or [".git", "pyproject.toml", "requirements.txt"]
        
        if base_dir:
            self.root = Path(base_dir).resolve()
        else:
            self.root = self._detect_project_root()

        self.config_path = self.root / "config" / config_filename
        self.config: Dict[str, Any] = {}
        # Stores resolved absolute paths
        self.paths: Dict[str, Path] = {} 
        
        self.load_config()

    def _detect_project_root(self) -> Path:
        """Walks up the directory tree to find the project root via markers."""
        # Fix: Start searching from the invoking script/module, not necessarily the library location
        # If this lib is installed in site-packages, __file__ is useless for root detection.
        # We try to use the current working directory or the caller's stack.
        
        current = Path(os.getcwd()).resolve()
        
        # Max depth search (e.g. 10 levels up)
        for _ in range(10): 
            for marker in self.root_markers:
                if (current / marker).exists():
                    return current
            
            # Fallback: check for 'config' folder with our config file
            if (current / "config" / self.config_filename).exists():
                return current
                
            if current.parent == current: # Reached filesystem root
                break
            current = current.parent
            
        return Path(os.getcwd()) # Fallback to CWD

    def load_config(self):
        """Loads and parses the configuration (YAML or TOML)."""
        if not self.config_path.exists():
            # Silently skip if not found - ConfigManager is the primary config source in V2
            return

        # Determine file type
        suffix = self.config_path.suffix.lower()
        
        if suffix in (".yaml", ".yml"):
            if not yaml:
                return  # Silently skip if yaml not available
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"❌ PathManager: Error loading YAML config: {e}")
        elif suffix == ".toml":
            if not tomllib:
                print("❌ PathManager Error: No TOML parser found (tomllib, tomli, or toml required).")
                return
            try:
                with open(self.config_path, "r" if hasattr(tomllib, "load") and tomllib.__name__ == "toml" else "rb") as f:
                    self.config = tomllib.load(f)
            except Exception as e:
                print(f"❌ PathManager: Error loading config: {e}")

    def resolve_path(self, path_str: str, context_vars: Dict[str, str] = None) -> Path:
        """
        Resolves a path string into an absolute Path object.
        Supports:
        - Tilde expansion (~/...)
        - Variable substitution ($var or ${var}) using provided context_vars
        """
        if not path_str:
            return Path(".")

        expanded_str = path_str
        
        # 1. Substitute variables if context provided
        if context_vars:
            for key, val in context_vars.items():
                if val:
                    pattern = re.compile(re.escape(f"${key}") + r"|" + re.escape(f"${{{key}}}") )
                    expanded_str = pattern.sub(str(val), expanded_str)

        # 2. Expand User (~)
        expanded_str = os.path.expanduser(expanded_str)
        
        # 3. Resolve absolute
        return Path(expanded_str).resolve()

    def get_config_value(self, section: str, key: str, default: Any = None) -> Any:
        """Safely retrieves a value from the config dict."""
        return self.config.get(section, {}).get(key, default)

    # --- API / Network Utilities ---

    def get_api_route(self, 
                      host_key: str, 
                      port_key: str, 
                      endpoint: str = "", 
                      section: str = "server", 
                      default_host: str = "127.0.0.1", 
                      default_port: int = 8000,
                      protocol: str = "http") -> str:
        """
        Constructs a full API URL.
        Example: http://localhost:8000/v1/models
        """
        host = self.get_config_value(section, host_key, default_host)
        port = self.get_config_value(section, port_key, default_port)
        
        # Clean endpoint syntax
        if endpoint and not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
            
        return f"{protocol}://{host}:{port}{endpoint}"
