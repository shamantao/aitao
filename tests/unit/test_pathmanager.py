"""
Unit tests for PathManager (US-001).

Tests all path accessors and directory creation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.core.pathmanager import AitaoPathManager


class TestPathManager:
    """Test suite for PathManager."""
    
    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project structure for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create project markers
        (temp_dir / "aitao.sh").touch()
        (temp_dir / "requirements.txt").touch()
        
        # Create config directory with minimal config.toml
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        
        config_content = """
[system]
storage_root = "data"
logs_path = "$storage_root/logs"

[models]
models_dir = "../AI-models"

[indexing]
include_paths = []
exclude_dirs = []
"""
        (config_dir / "config.toml").write_text(config_content)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_pathmanager_initialization(self, temp_project_root, monkeypatch):
        """Test PathManager initializes correctly."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
    
        assert pm.root.resolve() == temp_project_root.resolve()
        assert pm.config_path.resolve() == (temp_project_root / "config" / "config.toml").resolve()
        assert pm.config is not None
    
    def test_get_storage_root(self, temp_project_root, monkeypatch):
        """Test get_storage_root returns correct path."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        storage_root = pm.get_storage_root()
    
        assert storage_root.resolve() == (temp_project_root / "data").resolve()
        assert storage_root.exists()
    
    def test_get_logs_dir(self, temp_project_root, monkeypatch):
        """Test get_logs_dir returns correct path."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        logs_dir = pm.get_logs_dir()
    
        assert logs_dir.resolve() == (temp_project_root / "data" / "logs").resolve()
        assert logs_dir.exists()
    
    def test_get_models_dir(self, temp_project_root, monkeypatch):
        """Test get_models_dir returns correct path."""
        monkeypatch.chdir(temp_project_root)
        
        pm = AitaoPathManager()
        models_dir = pm.get_models_dir()
        
        # Should be parent/AI-models (from config)
        expected = temp_project_root.parent / "AI-models"
        assert models_dir.resolve() == expected.resolve()
        # Note: models_dir is external to project, not created by PathManager
    
    def test_get_cache_dir_base(self, temp_project_root, monkeypatch):
        """Test get_cache_dir returns base cache directory."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        cache_dir = pm.get_cache_dir()
    
        assert cache_dir.resolve() == (temp_project_root / "data" / "cache").resolve()
        assert cache_dir.exists()
    
    def test_get_cache_dir_ocr(self, temp_project_root, monkeypatch):
        """Test get_cache_dir with ocr type."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        ocr_cache = pm.get_cache_dir("ocr")
    
        assert ocr_cache.resolve() == (temp_project_root / "data" / "cache" / "ocr").resolve()
        assert ocr_cache.exists()
    
    def test_get_cache_dir_translations(self, temp_project_root, monkeypatch):
        """Test get_cache_dir with translations type."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        trans_cache = pm.get_cache_dir("translations")
    
        assert trans_cache.resolve() == (temp_project_root / "data" / "cache" / "translations").resolve()
        assert trans_cache.exists()
    
    def test_get_corrections_dir(self, temp_project_root, monkeypatch):
        """Test get_corrections_dir returns correct path."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        corrections_dir = pm.get_corrections_dir()
    
        assert corrections_dir.resolve() == (temp_project_root / "data" / "corrections").resolve()
        assert corrections_dir.exists()
    
    def test_get_vector_db_path(self, temp_project_root, monkeypatch):
        """Test get_vector_db_path returns correct path."""
        monkeypatch.chdir(temp_project_root)
    
        pm = AitaoPathManager()
        lancedb_path = pm.get_vector_db_path()
    
        assert lancedb_path.resolve() == (temp_project_root / "data" / "lancedb").resolve()
        assert lancedb_path.exists()
    
    def test_directory_structure_created(self, temp_project_root, monkeypatch):
        """Test all required directories are created on initialization."""
        monkeypatch.chdir(temp_project_root)
        
        pm = AitaoPathManager()
        storage = pm.get_storage_root()
        
        # Check all V2 directories exist
        assert (storage / "lancedb").exists()
        assert (storage / "queue").exists()
        assert (storage / "cache").exists()
        assert (storage / "cache" / "ocr").exists()
        assert (storage / "cache" / "translations").exists()
        assert (storage / "corrections").exists()
        assert (storage / "logs").exists()
    
    def test_get_indexing_config(self, temp_project_root, monkeypatch):
        """Test get_indexing_config returns correct structure."""
        monkeypatch.chdir(temp_project_root)
        
        pm = AitaoPathManager()
        indexing_config = pm.get_indexing_config()
        
        assert isinstance(indexing_config, dict)
        assert "include_paths" in indexing_config
        assert "exclude_dirs" in indexing_config
        assert isinstance(indexing_config["include_paths"], list)
    
    def test_variable_substitution(self, temp_project_root, monkeypatch):
        """Test $storage_root variable substitution in config."""
        monkeypatch.chdir(temp_project_root)
        
        pm = AitaoPathManager()
        logs_dir = pm.get_logs_dir()
        storage_root = pm.get_storage_root()
        
        # logs_path = "$storage_root/logs" should resolve correctly
        assert logs_dir == storage_root / "logs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
