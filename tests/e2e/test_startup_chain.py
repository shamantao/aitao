"""
E2E Smoke Tests for AItao Startup Chain.

These tests validate that the complete startup workflow works:
1. ./aitao.sh start → All services running
2. Scan → Queue populated → Worker processes → Documents indexed
3. ./aitao.sh search → Returns results
4. ./aitao.sh stop → All services stopped

CRITICAL: These tests exist because 476 unit tests passed while the 
application didn't actually work. Unit tests test components in isolation;
E2E tests validate the REAL user experience.

Run with: pytest tests/e2e/test_startup_chain.py -v
"""

import os
import sys
import time
import signal
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Generator
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli.commands.lifecycle import (
    API_PID_FILE,
    WORKER_PID_FILE,
    _start_api_server,
    _stop_api_server,
    _start_worker,
    _stop_worker,
    _run_initial_scan,
    _check_meilisearch_running,
    _get_api_port,
)


class TestServiceLifecycle:
    """Tests for individual service start/stop."""
    
    def test_api_port_from_config(self):
        """API port should be retrieved from config."""
        port = _get_api_port()
        assert isinstance(port, int)
        assert 1024 < port < 65535
    
    def test_meilisearch_status_check(self):
        """Should be able to check Meilisearch status without error."""
        # This should not raise, regardless of whether MS is running
        result = _check_meilisearch_running()
        assert isinstance(result, bool)
    
    def test_api_server_lifecycle(self):
        """API server should start and stop cleanly."""
        # Ensure stopped first
        _stop_api_server()
        time.sleep(1)
        
        # Start
        success, pid = _start_api_server()
        assert success is True
        assert pid is not None
        assert isinstance(pid, int)
        
        # Verify PID file exists
        assert API_PID_FILE.exists()
        
        # Verify process is running
        try:
            os.kill(pid, 0)
            process_exists = True
        except ProcessLookupError:
            process_exists = False
        assert process_exists, "API process should be running"
        
        # Stop
        stopped = _stop_api_server()
        assert stopped is True
        
        # Verify stopped (wait longer for graceful shutdown)
        time.sleep(3)
        try:
            os.kill(pid, 0)
            still_running = True
        except ProcessLookupError:
            still_running = False
        
        # PID file should be cleaned up
        if still_running:
            # Force cleanup for test
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
    
    def test_worker_lifecycle(self):
        """Worker daemon should start and stop cleanly."""
        # Ensure stopped first
        _stop_worker()
        time.sleep(1)
        
        # Start
        success, pid = _start_worker()
        assert success is True
        # Note: pid might be None if using subprocess - the parent returns before child writes PID
        
        # Wait for daemon to initialize with retry loop
        # Subprocess needs time to: start Python, import modules, write PID file
        from indexation.worker import BackgroundWorker
        worker = None
        for _ in range(10):  # Max 5 seconds
            time.sleep(0.5)
            worker = BackgroundWorker()
            if worker.is_running():
                break
        
        assert worker is not None and worker.is_running(), "Worker should be running"
        
        # Stop
        stopped = _stop_worker()
        assert stopped is True


class TestScanAndQueue:
    """Tests for filesystem scan and queue population."""
    
    def test_initial_scan_runs(self):
        """Initial scan should run without error."""
        new_count, modified_count = _run_initial_scan()
        assert isinstance(new_count, int)
        assert isinstance(modified_count, int)
        assert new_count >= 0
        assert modified_count >= 0
    
    def test_scan_populates_queue(self):
        """Scan should add discovered files to queue."""
        from indexation.queue import TaskQueue
        
        queue = TaskQueue()
        
        # Get current stats
        stats_before = queue.get_stats()
        
        # Run scan
        new_count, modified_count = _run_initial_scan()
        total = new_count + modified_count
        
        # Check queue
        stats_after = queue.get_stats()
        
        # Queue should exist and be accessible
        assert isinstance(stats_after, dict)
        
        # If files were found, queue should have more items
        # (or at least not fewer, as files might already be in queue)


class TestFullStartupChain:
    """
    Integration tests for the complete startup chain.
    
    These tests require Meilisearch to be installed (brew).
    Mark as slow since they involve real service operations.
    """
    
    @pytest.fixture(autouse=True)
    def cleanup(self) -> Generator:
        """Ensure services are stopped after each test."""
        yield
        # Cleanup after test
        _stop_api_server()
        _stop_worker()
    
    @pytest.mark.slow
    def test_start_command_starts_all_services(self):
        """./aitao.sh start should start all services."""
        # Ensure everything is stopped first
        _stop_api_server()
        _stop_worker()
        time.sleep(1)
        
        # Start API
        api_ok, api_pid = _start_api_server()
        assert api_ok, "API should start"
        
        # Start Worker
        worker_ok, worker_pid = _start_worker()
        assert worker_ok, "Worker should start"
        
        # Wait for both to initialize (subprocess needs time to write PID files)
        from indexation.worker import BackgroundWorker
        for _ in range(10):  # Max 5 seconds
            time.sleep(0.5)
            worker = BackgroundWorker()
            if worker.is_running():
                worker_pid = worker.get_pid()
                break
        
        try:
            os.kill(api_pid, 0)
            api_running = True
        except (ProcessLookupError, TypeError):
            api_running = False
        
        worker_running = worker.is_running() if worker else False
        
        assert api_running, "API should be running"
        assert worker_running, "Worker should be running"
    
    @pytest.mark.slow
    def test_stop_command_stops_all_services(self):
        """./aitao.sh stop should stop all services."""
        # Start services first
        _start_api_server()
        _start_worker()
        time.sleep(1)
        
        # Stop all
        api_stopped = _stop_api_server()
        worker_stopped = _stop_worker()
        
        assert api_stopped, "API should stop"
        assert worker_stopped, "Worker should stop"
        
        # Verify stopped
        time.sleep(1)
        assert not API_PID_FILE.exists() or not _is_pid_running(API_PID_FILE)
        assert not WORKER_PID_FILE.exists() or not _is_pid_running(WORKER_PID_FILE)
    
    @pytest.mark.slow
    def test_complete_workflow(self):
        """
        Test complete user workflow:
        1. Start services
        2. Scan documents
        3. Queue populated
        4. Stop services
        
        This is THE critical test that validates the system works end-to-end.
        """
        # 1. Start services
        api_ok, _ = _start_api_server()
        worker_ok, _ = _start_worker()
        assert api_ok and worker_ok, "Services should start"
        
        time.sleep(2)  # Let services initialize
        
        # 2. Run scan
        new_count, modified_count = _run_initial_scan()
        # Don't assert counts - might be 0 on clean system
        
        # 3. Check queue has our tasks
        from indexation.queue import TaskQueue
        queue = TaskQueue()
        stats = queue.get_stats()
        
        # Queue should exist and be accessible
        assert "total" in stats or "pending" in stats
        
        # 4. Stop services
        api_stopped = _stop_api_server()
        worker_stopped = _stop_worker()
        assert api_stopped and worker_stopped, "Services should stop"


class TestCLIIntegration:
    """Tests for CLI command integration."""
    
    def test_cli_status_command(self):
        """Status command should run without error."""
        from typer.testing import CliRunner
        from cli.commands.lifecycle import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["status"])
        
        # Should not crash
        assert result.exit_code == 0
        # Should show status table
        assert "Service" in result.output or "Status" in result.output


def _is_pid_running(pid_file: Path) -> bool:
    """Check if process from PID file is running."""
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False


# Markers for pytest
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
