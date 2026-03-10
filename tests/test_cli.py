"""
Tests for CLI commands.

Tests the Typer-based CLI commands.
"""

import pytest
from typer.testing import CliRunner

import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.main import app


runner = CliRunner()


class TestCLIBasic:
    """Test basic CLI functionality."""
    
    def test_help(self):
        """Test --help option."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AItao V2" in result.stdout
        assert "status" in result.stdout
        assert "ms" in result.stdout
        assert "db" in result.stdout
        
    def test_version(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "aitao" in result.stdout.lower()
        
    def test_status(self):
        """Test status command runs without error."""
        result = runner.invoke(app, ["status"])
        # Should run (may have partial failures due to config)
        # but should not crash
        assert result.exit_code == 0


class TestMeilisearchCommands:
    """Test Meilisearch CLI commands."""
    
    def test_ms_help(self):
        """Test ms subcommand help."""
        result = runner.invoke(app, ["ms", "--help"])
        assert result.exit_code == 0
        assert "status" in result.stdout
        assert "start" in result.stdout
        assert "upgrade" in result.stdout
        
    def test_ms_status(self):
        """Test ms status command."""
        result = runner.invoke(app, ["ms", "status"])
        # May fail if Meilisearch not running, but should not crash
        assert result.exit_code in [0, 1]


class TestDatabaseCommands:
    """Test LanceDB CLI commands."""
    
    def test_db_help(self):
        """Test db subcommand help."""
        result = runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0
        assert "status" in result.stdout
        assert "stats" in result.stdout
        assert "clear" in result.stdout
        
    def test_db_status(self):
        """Test db status command."""
        result = runner.invoke(app, ["db", "status"])
        # Should work with default test database
        assert result.exit_code in [0, 1]


class TestConfigCommands:
    """Test config CLI commands."""
    
    def test_config_help(self):
        """Test config subcommand help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.stdout
        assert "validate" in result.stdout
        
    def test_config_show_no_file(self):
        """Test config show when file doesn't exist."""
        result = runner.invoke(app, ["config", "show"])
        # Should handle missing config gracefully
        assert result.exit_code in [0, 1]
