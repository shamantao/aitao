"""
Unit tests for ConfigManager.

Tests cover:
- YAML file loading
- Default values merging
- Nested key access (dot notation)
- Section retrieval
- Environment variable expansion
- Configuration validation
- Hot reload functionality
- Error handling
"""

import pytest
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config import ConfigManager, ConfigError, get_config


class TestConfigManager:
    """Test ConfigManager class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def minimal_config(self, temp_config_dir):
        """Create minimal valid config.yaml."""
        config_path = temp_config_dir / "config.yaml"
        config_data = {
            "paths": {
                "storage_root": "/tmp/test_storage",
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        return config_path
    
    @pytest.fixture
    def full_config(self, temp_config_dir):
        """Create full config.yaml with all sections."""
        config_path = temp_config_dir / "config.yaml"
        config_data = {
            "paths": {
                "storage_root": "/data/aitao",
                "models_dir": "/models",
            },
            "indexing": {
                "enabled": True,
                "interval_minutes": 30,
                "include_paths": ["/docs", "/files"],
            },
            "ocr": {
                "provider": "paddleocr",
                "languages": ["fr", "zh"],
            },
            "api": {
                "host": "0.0.0.0",
                "port": 9000,
            },
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        return config_path
    
    def test_config_manager_initialization(self, minimal_config):
        """Test ConfigManager initializes correctly."""
        config = ConfigManager(str(minimal_config))
        
        assert config.config_path == minimal_config
        assert config._config is not None
        assert "paths" in config._config
    
    def test_config_manager_missing_file(self, temp_config_dir):
        """Test ConfigManager raises error if file not found."""
        with pytest.raises(ConfigError, match="not found"):
            ConfigManager(str(temp_config_dir / "nonexistent.yaml"))
    
    def test_config_get_simple_key(self, minimal_config):
        """Test getting simple configuration value."""
        config = ConfigManager(str(minimal_config))
        
        storage = config.get("paths")
        assert storage is not None
        assert "storage_root" in storage
    
    def test_config_get_nested_key(self, minimal_config):
        """Test getting nested key with dot notation."""
        config = ConfigManager(str(minimal_config))
        
        storage_root = config.get("paths.storage_root")
        assert storage_root == "/tmp/test_storage"
    
    def test_config_get_with_default(self, minimal_config):
        """Test default value when key doesn't exist."""
        config = ConfigManager(str(minimal_config))
        
        value = config.get("nonexistent.key", "default_value")
        assert value == "default_value"
    
    def test_config_get_section(self, full_config):
        """Test getting entire configuration section."""
        config = ConfigManager(str(full_config))
        
        indexing = config.get_section("indexing")
        
        assert isinstance(indexing, dict)
        assert indexing["enabled"] is True
        assert indexing["interval_minutes"] == 30
        assert "/docs" in indexing["include_paths"]
    
    def test_config_get_section_nonexistent(self, minimal_config):
        """Test getting nonexistent section raises error."""
        config = ConfigManager(str(minimal_config))
        
        with pytest.raises(ConfigError, match="not found"):
            config.get_section("nonexistent_section")
    
    def test_config_set_value(self, minimal_config):
        """Test setting configuration value at runtime."""
        config = ConfigManager(str(minimal_config))
        
        config.set("api.port", 9999)
        
        assert config.get("api.port") == 9999
    
    def test_config_set_nested_value(self, minimal_config):
        """Test setting nested configuration value."""
        config = ConfigManager(str(minimal_config))
        
        config.set("new.nested.key", "value")
        
        assert config.get("new.nested.key") == "value"
    
    def test_config_defaults_merged(self, minimal_config):
        """Test defaults are merged with loaded config."""
        config = ConfigManager(str(minimal_config))
        
        # Should have default indexing section even if not in file
        indexing = config.get_section("indexing")
        assert "enabled" in indexing
        assert "interval_minutes" in indexing
    
    def test_config_user_values_override_defaults(self, full_config):
        """Test user values override defaults."""
        config = ConfigManager(str(full_config))
        
        # User specified 30 minutes, not default 60
        assert config.get("indexing.interval_minutes") == 30
        
        # User specified port 9000, not default 8200
        assert config.get("api.port") == 9000
    
    def test_config_env_var_expansion(self, temp_config_dir):
        """Test environment variable expansion."""
        config_path = temp_config_dir / "config.yaml"
        config_data = {
            "paths": {
                "storage_root": "${HOME}/aitao_data",
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        config = ConfigManager(str(config_path))
        
        storage = config.get("paths.storage_root")
        assert "${HOME}" not in storage
        assert "aitao_data" in storage
    
    def test_config_reload(self, temp_config_dir):
        """Test configuration hot reload."""
        config_path = temp_config_dir / "config.yaml"
        
        # Initial config
        config_data = {"paths": {"storage_root": "/tmp/v1"}}
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        config = ConfigManager(str(config_path))
        assert config.get("paths.storage_root") == "/tmp/v1"
        
        # Modify config
        import time
        time.sleep(0.1)  # Ensure mtime changes
        config_data["paths"]["storage_root"] = "/tmp/v2"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Reload
        config.reload()
        assert config.get("paths.storage_root") == "/tmp/v2"
    
    def test_config_reload_unchanged_file(self, minimal_config):
        """Test reload skips if file unchanged."""
        config = ConfigManager(str(minimal_config))
        
        # First reload
        config.reload()
        first_mtime = config._last_modified
        
        # Second reload (file unchanged)
        config.reload()
        second_mtime = config._last_modified
        
        assert first_mtime == second_mtime
    
    def test_config_invalid_yaml(self, temp_config_dir):
        """Test error on invalid YAML syntax."""
        config_path = temp_config_dir / "config.yaml"
        
        # Write invalid YAML
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: syntax: [[[")
        
        with pytest.raises(ConfigError, match="Invalid YAML"):
            ConfigManager(str(config_path))
    
    def test_config_missing_required_section(self, temp_config_dir):
        """Test validation fails if required section missing."""
        config_path = temp_config_dir / "config.yaml"
        
        # Config without required 'paths' section
        config_data = {"api": {"port": 8200}}
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        with pytest.raises(ConfigError, match="Missing required section"):
            ConfigManager(str(config_path))
    
    def test_config_thread_safe_access(self, minimal_config):
        """Test thread-safe configuration access."""
        import threading
        
        config = ConfigManager(str(minimal_config))
        results = []
        errors = []
        
        def read_config():
            try:
                for _ in range(100):
                    value = config.get("paths.storage_root")
                    results.append(value)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=read_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 1000
        assert all(r == "/tmp/test_storage" for r in results)


class TestGetConfigSingleton:
    """Test get_config singleton function."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        import src.core.config
        src.core.config._config_manager = None
        yield
        src.core.config._config_manager = None
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary config file."""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "config.yaml"
        
        config_data = {"paths": {"storage_root": "/tmp/singleton"}}
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        yield config_path
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_config_returns_singleton(self, temp_config):
        """Test get_config returns same instance."""
        config1 = get_config(str(temp_config))
        config2 = get_config()
        
        assert config1 is config2
    
    def test_get_config_initializes_once(self, temp_config):
        """Test configuration only loaded once."""
        config1 = get_config(str(temp_config))
        
        # Modify value in first instance
        config1.set("test.key", "value")
        
        # Get "new" instance
        config2 = get_config()
        
        # Should have the modified value (same instance)
        assert config2.get("test.key") == "value"
