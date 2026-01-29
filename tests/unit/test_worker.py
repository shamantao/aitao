"""
Unit tests for BackgroundWorker.

Tests the background worker system for document processing, including:
- Worker initialization and configuration
- Task processing flow
- CPU load monitoring
- PID file management
- Error handling and retry logic
"""

import os
import time
import tempfile
import signal
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, PropertyMock
from dataclasses import dataclass
from typing import Optional

# Import test subjects
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from indexation.worker import (
    BackgroundWorker,
    WorkerConfig,
    WorkerStats
)
from indexation.queue import TaskQueue, Task, TaskStatus


# Mock IndexResult for tests
@dataclass
class MockIndexResult:
    """Mock IndexResult for testing."""
    path: str = "/test/doc.txt"
    doc_id: str = "test-doc-id"
    success: bool = True
    lancedb_indexed: bool = True
    meilisearch_indexed: bool = True
    error: Optional[str] = None
    word_count: int = 100


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_queue(temp_dir):
    """Create a TaskQueue with temporary storage."""
    queue_file = temp_dir / "queue" / "tasks.json"
    return TaskQueue(queue_file=str(queue_file))


@pytest.fixture
def worker(temp_dir, temp_queue):
    """Create a BackgroundWorker with temporary storage."""
    worker = BackgroundWorker(queue=temp_queue)
    worker.pid_file = temp_dir / "worker.pid"
    return worker


@pytest.fixture
def sample_task(temp_queue) -> Task:
    """Create a sample task in the queue."""
    return temp_queue.add_task("/test/document.pdf", task_type="index")


# ==============================================================================
# WorkerConfig Tests
# ==============================================================================

class TestWorkerConfig:
    """Tests for WorkerConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = WorkerConfig()
        
        assert config.poll_interval == 30
        assert config.cpu_threshold == 80.0
        assert config.max_consecutive_errors == 5
        assert config.error_pause_time == 60
        assert config.shutdown_timeout == 30
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = WorkerConfig(
            poll_interval=10,
            cpu_threshold=90.0,
            max_consecutive_errors=3
        )
        
        assert config.poll_interval == 10
        assert config.cpu_threshold == 90.0
        assert config.max_consecutive_errors == 3


# ==============================================================================
# WorkerStats Tests
# ==============================================================================

class TestWorkerStats:
    """Tests for WorkerStats dataclass."""
    
    def test_default_values(self):
        """Test default stats values."""
        stats = WorkerStats()
        
        assert stats.started_at is None
        assert stats.tasks_processed == 0
        assert stats.tasks_failed == 0
        assert stats.is_running is False
        assert stats.is_paused is False
    
    def test_to_dict(self):
        """Test stats serialization."""
        stats = WorkerStats(
            started_at="2025-01-28T10:00:00",
            tasks_processed=5,
            is_running=True
        )
        
        data = stats.to_dict()
        
        assert data["started_at"] == "2025-01-28T10:00:00"
        assert data["tasks_processed"] == 5
        assert data["is_running"] is True


# ==============================================================================
# BackgroundWorker Initialization Tests
# ==============================================================================

class TestWorkerInit:
    """Tests for BackgroundWorker initialization."""
    
    def test_init_with_queue(self, temp_queue):
        """Test initialization with provided queue."""
        worker = BackgroundWorker(queue=temp_queue)
        
        assert worker.queue is temp_queue
        assert worker.stats.is_running is False
        assert worker._shutdown_requested is False
    
    def test_init_default_config(self, worker):
        """Test default worker configuration."""
        assert worker.worker_config.poll_interval == 30
        assert worker.worker_config.cpu_threshold == 80.0
    
    def test_init_creates_signal_handlers(self, worker):
        """Test that signal handlers are registered."""
        # This is hard to test directly, but we can verify the handler method exists
        assert hasattr(worker, '_handle_shutdown')
        assert callable(worker._handle_shutdown)


# ==============================================================================
# Task Processing Tests
# ==============================================================================

class TestTaskProcessing:
    """Tests for task processing."""
    
    @patch('indexation.worker.DocumentIndexer')
    def test_default_handler_succeeds(self, mock_indexer_class, worker, sample_task):
        """Test default handler processes task successfully when file exists."""
        # Mock the indexer to return success with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True, word_count=50)
        mock_indexer_class.return_value = mock_indexer
        
        # Create a temp file for the task
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            sample_task.file_path = temp_path
            result = worker._default_handler(sample_task)
            assert result is True
        finally:
            os.unlink(temp_path)
    
    @patch('indexation.worker.DocumentIndexer')
    def test_process_task_updates_queue(self, mock_indexer_class, worker, temp_queue, sample_task):
        """Test that processing updates task status in queue."""
        # Mock the indexer to return success with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create a temp file for the task
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            sample_task.file_path = f.name
        
        try:
            worker._process_task(sample_task)
            
            updated = temp_queue.get_task(sample_task.id)
            assert updated.status == TaskStatus.COMPLETED.value
        finally:
            os.unlink(sample_task.file_path)
    
    @patch('indexation.worker.DocumentIndexer')
    def test_process_task_increments_stats(self, mock_indexer_class, worker, sample_task):
        """Test that processing increments stats."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        assert worker.stats.tasks_processed == 0
        
        # Create a temp file for the task
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            sample_task.file_path = f.name
        
        try:
            worker._process_task(sample_task)
            
            assert worker.stats.tasks_processed == 1
            assert worker.stats.tasks_failed == 0
        finally:
            os.unlink(sample_task.file_path)
    
    def test_process_task_handles_failure(self, worker, temp_queue, sample_task):
        """Test that failed tasks are handled correctly."""
        def failing_handler(task):
            raise Exception("Test error")
        
        worker.task_handler = failing_handler
        result = worker._process_task(sample_task)
        
        assert result is False
        assert worker.stats.tasks_failed == 1
        
        updated = temp_queue.get_task(sample_task.id)
        assert updated.status == TaskStatus.FAILED.value
        assert updated.error_message == "Test error"
    
    def test_custom_handler_called(self, worker, sample_task):
        """Test that custom handler is called."""
        handler_called = False
        
        def custom_handler(task):
            nonlocal handler_called
            handler_called = True
            return True
        
        worker.task_handler = custom_handler
        worker._process_task(sample_task)
        
        assert handler_called is True
    
    def test_consecutive_errors_tracked(self, worker, temp_queue):
        """Test that consecutive errors are tracked."""
        def failing_handler(task):
            raise Exception("Error")
        
        worker.task_handler = failing_handler
        
        # Add multiple tasks
        for i in range(3):
            temp_queue.add_task(f"/test/doc{i}.pdf")
        
        # Process them (all will fail)
        for _ in range(3):
            task = temp_queue.get_next_task()
            if task:
                worker._process_task(task)
        
        assert worker.stats.consecutive_errors == 3
    
    @patch('indexation.worker.DocumentIndexer')
    def test_success_resets_consecutive_errors(self, mock_indexer_class, worker, temp_queue):
        """Test that success resets consecutive error count."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        worker.stats.consecutive_errors = 3
        
        # Create a temp file for the task
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            task = temp_queue.add_task(temp_path)
            worker._process_task(task)
            
            assert worker.stats.consecutive_errors == 0
        finally:
            os.unlink(temp_path)


# ==============================================================================
# Poll and Process Tests
# ==============================================================================

class TestPollAndProcess:
    """Tests for poll and process cycle."""
    
    def test_poll_empty_queue(self, worker):
        """Test polling empty queue returns False."""
        result = worker._poll_and_process()
        
        assert result is False
    
    @patch('indexation.worker.DocumentIndexer')
    def test_poll_processes_task(self, mock_indexer_class, worker, temp_queue, temp_dir):
        """Test polling processes pending task."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create a real temp file
        test_file = temp_dir / "test_doc.txt"
        test_file.write_text("test content")
        temp_queue.add_task(str(test_file), task_type="index")
        
        result = worker._poll_and_process()
        
        assert result is True
        assert worker.stats.tasks_processed == 1
    
    def test_poll_updates_last_poll(self, worker):
        """Test that poll updates last_poll timestamp."""
        assert worker.stats.last_poll is None
        
        worker._poll_and_process()
        
        assert worker.stats.last_poll is not None
    
    @patch('indexation.worker.psutil.cpu_percent')
    def test_poll_skips_high_cpu(self, mock_cpu, worker, sample_task):
        """Test that poll skips processing when CPU is high."""
        mock_cpu.return_value = 95.0  # Above threshold
        
        result = worker._poll_and_process()
        
        assert result is False
        assert worker.stats.is_paused is True
        assert "CPU" in worker.stats.pause_reason
    
    @patch('indexation.worker.DocumentIndexer')
    @patch('indexation.worker.psutil.cpu_percent')
    def test_poll_processes_normal_cpu(self, mock_cpu, mock_indexer_class, worker, temp_queue, temp_dir):
        """Test that poll processes when CPU is normal."""
        mock_cpu.return_value = 30.0  # Below threshold
        
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create a real temp file
        test_file = temp_dir / "test_doc.txt"
        test_file.write_text("test content")
        temp_queue.add_task(str(test_file), task_type="index")
        
        result = worker._poll_and_process()
        
        assert result is True
        assert worker.stats.is_paused is False


# ==============================================================================
# System Load Tests
# ==============================================================================

class TestSystemLoad:
    """Tests for system load monitoring."""
    
    @patch('indexation.worker.psutil.cpu_percent')
    def test_check_load_below_threshold(self, mock_cpu, worker):
        """Test load check passes when CPU is low."""
        mock_cpu.return_value = 50.0
        
        can_process, reason = worker._check_system_load()
        
        assert can_process is True
        assert reason == ""
    
    @patch('indexation.worker.psutil.cpu_percent')
    def test_check_load_above_threshold(self, mock_cpu, worker):
        """Test load check fails when CPU is high."""
        mock_cpu.return_value = 90.0
        
        can_process, reason = worker._check_system_load()
        
        assert can_process is False
        assert "CPU" in reason
    
    @patch('indexation.worker.psutil.cpu_percent')
    def test_check_load_handles_error(self, mock_cpu, worker):
        """Test load check handles errors gracefully."""
        mock_cpu.side_effect = Exception("psutil error")
        
        can_process, reason = worker._check_system_load()
        
        # Should return True (continue) if we can't check
        assert can_process is True


# ==============================================================================
# PID File Tests
# ==============================================================================

class TestPidFile:
    """Tests for PID file management."""
    
    def test_write_pid_file(self, worker, temp_dir):
        """Test writing PID file."""
        worker._write_pid_file()
        
        assert worker.pid_file.exists()
        assert worker.pid_file.read_text() == str(os.getpid())
    
    def test_remove_pid_file(self, worker, temp_dir):
        """Test removing PID file."""
        worker._write_pid_file()
        assert worker.pid_file.exists()
        
        worker._remove_pid_file()
        assert not worker.pid_file.exists()
    
    def test_remove_nonexistent_pid_file(self, worker, temp_dir):
        """Test removing nonexistent PID file doesn't raise."""
        assert not worker.pid_file.exists()
        
        # Should not raise
        worker._remove_pid_file()
    
    def test_is_running_without_pid_file(self, worker, temp_dir):
        """Test is_running returns False without PID file."""
        assert worker.is_running() is False
    
    def test_is_running_with_current_pid(self, worker, temp_dir):
        """Test is_running returns True for current process."""
        worker._write_pid_file()
        
        assert worker.is_running() is True
    
    def test_is_running_with_stale_pid(self, worker, temp_dir):
        """Test is_running returns False for stale PID."""
        # Write a fake PID that doesn't exist
        worker.pid_file.parent.mkdir(parents=True, exist_ok=True)
        worker.pid_file.write_text("99999999")
        
        assert worker.is_running() is False
    
    def test_get_pid_without_file(self, worker):
        """Test get_pid returns None without PID file."""
        assert worker.get_pid() is None
    
    def test_get_pid_with_file(self, worker, temp_dir):
        """Test get_pid returns correct PID."""
        worker._write_pid_file()
        
        assert worker.get_pid() == os.getpid()


# ==============================================================================
# Run Once Tests
# ==============================================================================

class TestRunOnce:
    """Tests for run_once method."""
    
    def test_run_once_empty_queue(self, worker):
        """Test run_once with empty queue."""
        result = worker.run_once()
        
        assert result is False
    
    @patch('indexation.worker.DocumentIndexer')
    def test_run_once_processes_task(self, mock_indexer_class, worker, temp_queue, temp_dir):
        """Test run_once processes a single task."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create a real temp file
        test_file = temp_dir / "test_doc.txt"
        test_file.write_text("test content")
        temp_queue.add_task(str(test_file), task_type="index")
        
        result = worker.run_once()
        
        assert result is True
        assert worker.stats.tasks_processed == 1
    
    @patch('indexation.worker.DocumentIndexer')
    def test_run_once_does_not_loop(self, mock_indexer_class, worker, temp_queue, temp_dir):
        """Test run_once only processes one task."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create real temp files
        test_file1 = temp_dir / "doc1.txt"
        test_file1.write_text("test content 1")
        test_file2 = temp_dir / "doc2.txt"
        test_file2.write_text("test content 2")
        
        temp_queue.add_task(str(test_file1))
        temp_queue.add_task(str(test_file2))
        
        worker.run_once()
        
        assert worker.stats.tasks_processed == 1
        
        # Queue should still have one pending
        stats = temp_queue.get_stats()
        assert stats["pending"] == 1


# ==============================================================================
# Shutdown Tests
# ==============================================================================

class TestShutdown:
    """Tests for graceful shutdown."""
    
    def test_handle_shutdown_sets_flag(self, worker):
        """Test shutdown handler sets flag."""
        assert worker._shutdown_requested is False
        
        worker._handle_shutdown(signal.SIGTERM, None)
        
        assert worker._shutdown_requested is True
    
    def test_handle_shutdown_sigint(self, worker):
        """Test shutdown handler for SIGINT."""
        worker._handle_shutdown(signal.SIGINT, None)
        
        assert worker._shutdown_requested is True


# ==============================================================================
# Get Stats Tests
# ==============================================================================

class TestGetStats:
    """Tests for get_stats method."""
    
    def test_get_stats_returns_dict(self, worker):
        """Test get_stats returns a dictionary."""
        stats = worker.get_stats()
        
        assert isinstance(stats, dict)
        assert "tasks_processed" in stats
        assert "is_running" in stats
    
    @patch('indexation.worker.DocumentIndexer')
    def test_get_stats_reflects_state(self, mock_indexer_class, worker, temp_queue, temp_dir):
        """Test get_stats reflects worker state."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create a real temp file
        test_file = temp_dir / "test_doc.txt"
        test_file.write_text("test content")
        task = temp_queue.add_task(str(test_file), task_type="index")
        
        worker._process_task(task)
        
        stats = worker.get_stats()
        
        assert stats["tasks_processed"] == 1
        assert stats["last_task_id"] == task.id


# ==============================================================================
# Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_handler_returns_false(self, worker, temp_queue, sample_task):
        """Test handler that returns False."""
        def false_handler(task):
            return False
        
        worker.task_handler = false_handler
        result = worker._process_task(sample_task)
        
        assert result is False
        assert worker.stats.tasks_failed == 1
    
    @patch('indexation.worker.DocumentIndexer')
    def test_multiple_tasks_sequential(self, mock_indexer_class, worker, temp_queue, temp_dir):
        """Test processing multiple tasks sequentially."""
        # Mock the indexer with proper IndexResult
        mock_indexer = MagicMock()
        mock_indexer.index_file.return_value = MockIndexResult(success=True)
        mock_indexer_class.return_value = mock_indexer
        
        # Create real temp files
        for i in range(5):
            test_file = temp_dir / f"doc{i}.txt"
            test_file.write_text(f"test content {i}")
            temp_queue.add_task(str(test_file))
        
        for _ in range(5):
            worker.run_once()
        
        assert worker.stats.tasks_processed == 5
    
    def test_worker_config_from_dict(self, temp_queue):
        """Test worker can be configured from config dict."""
        # This tests the config loading path
        worker = BackgroundWorker(queue=temp_queue)
        
        # Default values should be set
        assert worker.worker_config.poll_interval == 30
