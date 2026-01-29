"""
Tests for lifecycle commands (start/stop/restart services).

Test coverage for:
- Start command
- Stop command  
- Restart command
- Lifecycle group commands
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli.main import app
from cli.commands import lifecycle

runner = CliRunner()


class TestRootLifecycleCommands:
    """Test start/stop/restart at root level (user-friendly interface)."""
    
    @patch("cli.commands.lifecycle._run_command")
    def test_start_command(self, mock_run):
        """Test root-level 'start' command starts all services."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "Starting all AItao services" in result.stdout
        # Should call both services
        assert mock_run.call_count == 2
    
    @patch("cli.commands.lifecycle._run_command")
    def test_stop_command(self, mock_run):
        """Test root-level 'stop' command stops all services."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["stop"])
        
        assert result.exit_code == 0
        assert "Stopping all AItao services" in result.stdout
        # Should call both services (Worker first, then Meilisearch)
        assert mock_run.call_count == 2
    
    @patch("cli.commands.lifecycle._run_command")
    @patch("time.sleep")  # Mock sleep to speed up test
    @patch("subprocess.run")
    def test_restart_command(self, mock_subprocess, mock_sleep, mock_run):
        """Test root-level 'restart' command restarts all services."""
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        result = runner.invoke(app, ["restart"])
        
        # Should complete without error
        assert result.exit_code == 0
        assert "Restarting all AItao services" in result.stdout
    
    @patch("cli.commands.lifecycle._run_command")
    def test_start_failure_handling(self, mock_run):
        """Test start command handles service failures."""
        # First service fails
        mock_run.side_effect = [False, True]
        
        result = runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "Some services failed to start" in result.stdout


class TestLifecycleGroupCommands:
    """Test lifecycle group commands (./aitao.sh lifecycle start, etc.)."""
    
    @patch("cli.commands.lifecycle._run_command")
    def test_lifecycle_start_group(self, mock_run):
        """Test 'lifecycle start' group command."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["lifecycle", "start"])
        
        assert result.exit_code == 0
        assert "Starting all AItao services" in result.stdout
    
    @patch("cli.commands.lifecycle._run_command")
    def test_lifecycle_stop_group(self, mock_run):
        """Test 'lifecycle stop' group command."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["lifecycle", "stop"])
        
        assert result.exit_code == 0
        assert "Stopping all AItao services" in result.stdout
    
    @patch("cli.commands.lifecycle._run_command")
    @patch("time.sleep")
    @patch("subprocess.run")
    def test_lifecycle_restart_group(self, mock_subprocess, mock_sleep, mock_run):
        """Test 'lifecycle restart' group command."""
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        result = runner.invoke(app, ["lifecycle", "restart"])
        
        assert result.exit_code == 0


class TestServiceCommands:
    """Test individual service management via lifecycle."""
    
    @patch("cli.commands.lifecycle._run_command")
    def test_start_order(self, mock_run):
        """Test that services are started in correct order."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["start"])
        
        # Should start Meilisearch first, then Worker
        calls = mock_run.call_args_list
        assert len(calls) >= 2
        # First call: Meilisearch
        assert "Meilisearch" in str(calls[0])
        # Second call: Worker
        assert "Worker" in str(calls[1])
    
    @patch("cli.commands.lifecycle._run_command")
    def test_stop_order(self, mock_run):
        """Test that services are stopped in correct order (reverse of start)."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["stop"])
        
        # Should stop Worker first (it may be processing), then Meilisearch
        calls = mock_run.call_args_list
        assert len(calls) >= 2
        # First call: Worker
        assert "Worker" in str(calls[0])
        # Second call: Meilisearch
        assert "Meilisearch" in str(calls[1])


class TestVerboseOutput:
    """Test verbose output flag."""
    
    @patch("cli.commands.lifecycle._run_command")
    def test_verbose_flag_accepted(self, mock_run):
        """Test that verbose flag is accepted."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["start", "-v"])
        assert result.exit_code == 0
        
        result = runner.invoke(app, ["start", "--verbose"])
        assert result.exit_code == 0
    
    @patch("cli.commands.lifecycle._run_command")
    def test_stop_verbose_flag(self, mock_run):
        """Test verbose flag with stop command."""
        mock_run.return_value = True
        
        result = runner.invoke(app, ["stop", "--verbose"])
        assert result.exit_code == 0


class TestCommandHelp:
    """Test help messages for lifecycle commands."""
    
    def test_start_help(self):
        """Test start command help."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start all AItao services" in result.stdout
        assert "Meilisearch" in result.stdout
        assert "Worker" in result.stdout
    
    def test_stop_help(self):
        """Test stop command help."""
        result = runner.invoke(app, ["stop", "--help"])
        assert result.exit_code == 0
        assert "Stop all AItao services" in result.stdout
    
    def test_restart_help(self):
        """Test restart command help."""
        result = runner.invoke(app, ["restart", "--help"])
        assert result.exit_code == 0
        assert "Restart all AItao services" in result.stdout
    
    def test_lifecycle_group_help(self):
        """Test lifecycle group help."""
        result = runner.invoke(app, ["lifecycle", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "restart" in result.stdout
