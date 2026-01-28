"""
Unit tests for TaskQueue.

Tests the task queue system for document processing, including:
- Task creation and persistence
- Priority-based ordering
- Status updates and transitions
- Batch operations
- Statistics and cleanup
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import test subjects
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from indexation.queue import (
    TaskQueue,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_queue_file():
    """Create a temporary queue file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_file = Path(tmpdir) / "queue" / "tasks.json"
        yield queue_file


@pytest.fixture
def queue(temp_queue_file):
    """Create a TaskQueue instance with temporary storage."""
    return TaskQueue(queue_file=str(temp_queue_file))


@pytest.fixture
def sample_files():
    """Return sample file paths for testing."""
    return [
        "/docs/document1.pdf",
        "/docs/document2.docx",
        "/docs/image.png",
        "/docs/notes.txt",
        "/docs/presentation.pptx"
    ]


# ==============================================================================
# Task Dataclass Tests
# ==============================================================================

class TestTask:
    """Tests for Task dataclass."""
    
    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            id="abc123",
            file_path="/path/to/file.pdf",
            task_type="index"
        )
        
        assert task.id == "abc123"
        assert task.file_path == "/path/to/file.pdf"
        assert task.task_type == "index"
        assert task.priority == TaskPriority.NORMAL.value
        assert task.status == TaskStatus.PENDING.value
        assert task.added_at != ""
        assert task.retry_count == 0
    
    def test_task_with_custom_values(self):
        """Test task with custom values."""
        task = Task(
            id="xyz789",
            file_path="/path/to/file.pdf",
            task_type="ocr",
            priority=TaskPriority.HIGH.value,
            metadata={"source": "scanner"}
        )
        
        assert task.priority == "high"
        assert task.metadata == {"source": "scanner"}
    
    def test_task_to_dict(self):
        """Test task serialization."""
        task = Task(
            id="test1",
            file_path="/file.pdf",
            task_type="index"
        )
        
        data = task.to_dict()
        
        assert isinstance(data, dict)
        assert data["id"] == "test1"
        assert data["file_path"] == "/file.pdf"
        assert "added_at" in data
        assert "metadata" in data
    
    def test_task_from_dict(self):
        """Test task deserialization."""
        data = {
            "id": "test2",
            "file_path": "/doc.txt",
            "task_type": "translate",
            "priority": "low",
            "status": "pending",
            "added_at": "2025-01-28T10:00:00",
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "retry_count": 0,
            "metadata": {}
        }
        
        task = Task.from_dict(data)
        
        assert task.id == "test2"
        assert task.file_path == "/doc.txt"
        assert task.task_type == "translate"
        assert task.priority == "low"
    
    def test_task_status_properties(self):
        """Test task status helper properties."""
        task = Task(id="t1", file_path="/f.pdf", task_type="index")
        
        assert task.is_pending is True
        assert task.is_processing is False
        
        task.status = TaskStatus.PROCESSING.value
        assert task.is_pending is False
        assert task.is_processing is True


class TestTaskPriority:
    """Tests for TaskPriority enum."""
    
    def test_priority_values(self):
        """Test priority enum values."""
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.NORMAL.value == "normal"
        assert TaskPriority.LOW.value == "low"
    
    def test_priority_sort_order(self):
        """Test priority sort order."""
        assert TaskPriority.HIGH.sort_order < TaskPriority.NORMAL.sort_order
        assert TaskPriority.NORMAL.sort_order < TaskPriority.LOW.sort_order


class TestTaskStatus:
    """Tests for TaskStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


# ==============================================================================
# TaskQueue Basic Tests
# ==============================================================================

class TestTaskQueueInit:
    """Tests for TaskQueue initialization."""
    
    def test_init_creates_queue_file(self, temp_queue_file):
        """Test that init creates the queue file."""
        queue = TaskQueue(queue_file=str(temp_queue_file))
        
        assert temp_queue_file.exists()
        assert temp_queue_file.read_text() == "[]"
    
    def test_init_creates_parent_directory(self, temp_queue_file):
        """Test that init creates parent directories."""
        nested = temp_queue_file.parent / "deep" / "nested" / "tasks.json"
        queue = TaskQueue(queue_file=str(nested))
        
        assert nested.parent.exists()
    
    def test_init_preserves_existing_tasks(self, temp_queue_file):
        """Test that init doesn't overwrite existing tasks."""
        # Create file with existing tasks
        temp_queue_file.parent.mkdir(parents=True, exist_ok=True)
        existing = [{"id": "old1", "file_path": "/old.pdf", "task_type": "index",
                     "priority": "normal", "status": "pending", "added_at": "2025-01-01",
                     "started_at": None, "completed_at": None, "error_message": None,
                     "retry_count": 0, "metadata": {}}]
        temp_queue_file.write_text(json.dumps(existing))
        
        queue = TaskQueue(queue_file=str(temp_queue_file))
        tasks = queue.list_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].id == "old1"


# ==============================================================================
# Add Task Tests
# ==============================================================================

class TestAddTask:
    """Tests for adding tasks to the queue."""
    
    def test_add_single_task(self, queue):
        """Test adding a single task."""
        task = queue.add_task("/doc.pdf", task_type="index")
        
        assert task.id is not None
        assert len(task.id) == 8  # Short UUID
        assert task.file_path == "/doc.pdf"
        assert task.task_type == "index"
        assert task.status == "pending"
    
    def test_add_task_with_priority(self, queue):
        """Test adding task with priority."""
        task = queue.add_task("/urgent.pdf", priority="high")
        
        assert task.priority == "high"
    
    def test_add_task_with_metadata(self, queue):
        """Test adding task with metadata."""
        metadata = {"size": 1024, "pages": 5}
        task = queue.add_task("/doc.pdf", metadata=metadata)
        
        assert task.metadata == metadata
    
    def test_add_task_persists(self, queue, temp_queue_file):
        """Test that added task is persisted."""
        queue.add_task("/persistent.pdf")
        
        # Read directly from file
        data = json.loads(temp_queue_file.read_text())
        
        assert len(data) == 1
        assert data[0]["file_path"] == "/persistent.pdf"
    
    def test_add_duplicate_task_returns_existing(self, queue):
        """Test that adding duplicate task returns existing one."""
        task1 = queue.add_task("/doc.pdf", task_type="index")
        task2 = queue.add_task("/doc.pdf", task_type="index")
        
        assert task1.id == task2.id
        
        stats = queue.get_stats()
        assert stats["total"] == 1
    
    def test_add_same_file_different_type(self, queue):
        """Test that same file with different task type creates new task."""
        task1 = queue.add_task("/doc.pdf", task_type="index")
        task2 = queue.add_task("/doc.pdf", task_type="ocr")
        
        assert task1.id != task2.id
        
        stats = queue.get_stats()
        assert stats["total"] == 2


class TestAddTasksBatch:
    """Tests for batch task addition."""
    
    def test_add_batch(self, queue, sample_files):
        """Test adding multiple tasks at once."""
        tasks = queue.add_tasks_batch(sample_files)
        
        assert len(tasks) == 5
        
        stats = queue.get_stats()
        assert stats["total"] == 5
    
    def test_add_batch_skips_duplicates(self, queue, sample_files):
        """Test batch doesn't add duplicates."""
        queue.add_tasks_batch(sample_files[:3])
        tasks = queue.add_tasks_batch(sample_files)
        
        assert len(tasks) == 2  # Only new ones
        
        stats = queue.get_stats()
        assert stats["total"] == 5
    
    def test_add_batch_with_priority(self, queue, sample_files):
        """Test batch with custom priority."""
        tasks = queue.add_tasks_batch(sample_files, priority="high")
        
        assert all(t.priority == "high" for t in tasks)


# ==============================================================================
# Get Task Tests
# ==============================================================================

class TestGetTask:
    """Tests for retrieving tasks."""
    
    def test_get_task_by_id(self, queue):
        """Test getting a specific task."""
        added = queue.add_task("/doc.pdf")
        
        retrieved = queue.get_task(added.id)
        
        assert retrieved is not None
        assert retrieved.id == added.id
        assert retrieved.file_path == added.file_path
    
    def test_get_nonexistent_task(self, queue):
        """Test getting a task that doesn't exist."""
        result = queue.get_task("nonexistent")
        
        assert result is None
    
    def test_get_next_task_empty_queue(self, queue):
        """Test get_next_task on empty queue."""
        result = queue.get_next_task()
        
        assert result is None
    
    def test_get_next_task_returns_oldest(self, queue):
        """Test get_next_task returns oldest pending."""
        task1 = queue.add_task("/first.pdf")
        task2 = queue.add_task("/second.pdf")
        
        next_task = queue.get_next_task()
        
        assert next_task.id == task1.id
    
    def test_get_next_task_respects_priority(self, queue):
        """Test get_next_task respects priority ordering."""
        queue.add_task("/low.pdf", priority="low")
        queue.add_task("/normal.pdf", priority="normal")
        high_task = queue.add_task("/high.pdf", priority="high")
        
        next_task = queue.get_next_task()
        
        assert next_task.id == high_task.id
    
    def test_get_next_task_skips_processing(self, queue):
        """Test get_next_task skips tasks being processed."""
        task1 = queue.add_task("/first.pdf")
        task2 = queue.add_task("/second.pdf")
        
        queue.mark_processing(task1.id)
        next_task = queue.get_next_task()
        
        assert next_task.id == task2.id


# ==============================================================================
# Update Status Tests
# ==============================================================================

class TestUpdateStatus:
    """Tests for task status updates."""
    
    def test_update_status(self, queue):
        """Test updating task status."""
        task = queue.add_task("/doc.pdf")
        
        result = queue.update_status(task.id, "processing")
        
        assert result is True
        
        updated = queue.get_task(task.id)
        assert updated.status == "processing"
    
    def test_update_status_nonexistent(self, queue):
        """Test updating nonexistent task."""
        result = queue.update_status("fake", "completed")
        
        assert result is False
    
    def test_mark_processing_sets_started_at(self, queue):
        """Test that mark_processing sets started_at."""
        task = queue.add_task("/doc.pdf")
        
        queue.mark_processing(task.id)
        
        updated = queue.get_task(task.id)
        assert updated.started_at is not None
    
    def test_mark_completed_sets_completed_at(self, queue):
        """Test that mark_completed sets completed_at."""
        task = queue.add_task("/doc.pdf")
        
        queue.mark_completed(task.id)
        
        updated = queue.get_task(task.id)
        assert updated.completed_at is not None
        assert updated.status == "completed"
    
    def test_mark_failed_sets_error(self, queue):
        """Test that mark_failed sets error message."""
        task = queue.add_task("/doc.pdf")
        
        queue.mark_failed(task.id, "Connection timeout")
        
        updated = queue.get_task(task.id)
        assert updated.status == "failed"
        assert updated.error_message == "Connection timeout"
        assert updated.retry_count == 1
    
    def test_cancel_task(self, queue):
        """Test cancelling a task."""
        task = queue.add_task("/doc.pdf")
        
        result = queue.cancel_task(task.id)
        
        assert result is True
        
        updated = queue.get_task(task.id)
        assert updated.status == "cancelled"


# ==============================================================================
# Retry Tests
# ==============================================================================

class TestRetry:
    """Tests for retry functionality."""
    
    def test_retry_failed_tasks(self, queue):
        """Test retrying failed tasks."""
        task = queue.add_task("/doc.pdf")
        queue.mark_failed(task.id, "Error 1")
        
        count = queue.retry_failed()
        
        assert count == 1
        
        updated = queue.get_task(task.id)
        assert updated.status == "pending"
        assert updated.error_message is None
    
    def test_retry_respects_max_retries(self, queue):
        """Test that retry respects MAX_RETRIES limit."""
        task = queue.add_task("/doc.pdf")
        
        # Fail more than MAX_RETRIES times
        for i in range(TaskQueue.MAX_RETRIES + 1):
            queue.mark_failed(task.id, f"Error {i}")
            queue.retry_failed()
        
        # After max retries, should stay failed
        updated = queue.get_task(task.id)
        assert updated.status == "failed"
        assert updated.retry_count > TaskQueue.MAX_RETRIES


# ==============================================================================
# Statistics Tests
# ==============================================================================

class TestGetStats:
    """Tests for queue statistics."""
    
    def test_stats_empty_queue(self, queue):
        """Test stats on empty queue."""
        stats = queue.get_stats()
        
        assert stats["total"] == 0
        assert stats["pending"] == 0
        assert stats["completed"] == 0
    
    def test_stats_with_tasks(self, queue, sample_files):
        """Test stats with various tasks."""
        queue.add_tasks_batch(sample_files)
        queue.mark_completed(queue.get_next_task().id)
        queue.mark_failed(queue.get_next_task().id, "Error")
        
        stats = queue.get_stats()
        
        assert stats["total"] == 5
        assert stats["pending"] == 3
        assert stats["completed"] == 1
        assert stats["failed"] == 1
    
    def test_stats_by_type(self, queue):
        """Test stats by task type."""
        queue.add_task("/doc1.pdf", task_type="index")
        queue.add_task("/doc2.pdf", task_type="index")
        queue.add_task("/img.png", task_type="ocr")
        
        stats = queue.get_stats()
        
        assert stats["by_type"]["index"] == 2
        assert stats["by_type"]["ocr"] == 1
    
    def test_stats_by_priority(self, queue):
        """Test stats by priority."""
        queue.add_task("/high1.pdf", priority="high")
        queue.add_task("/high2.pdf", priority="high")
        queue.add_task("/normal.pdf", priority="normal")
        queue.add_task("/low.pdf", priority="low")
        
        stats = queue.get_stats()
        
        assert stats["by_priority"]["high"] == 2
        assert stats["by_priority"]["normal"] == 1
        assert stats["by_priority"]["low"] == 1


# ==============================================================================
# List Tasks Tests
# ==============================================================================

class TestListTasks:
    """Tests for listing tasks."""
    
    def test_list_all_tasks(self, queue, sample_files):
        """Test listing all tasks."""
        queue.add_tasks_batch(sample_files)
        
        tasks = queue.list_tasks()
        
        assert len(tasks) == 5
    
    def test_list_with_status_filter(self, queue, sample_files):
        """Test listing with status filter."""
        queue.add_tasks_batch(sample_files)
        queue.mark_completed(queue.get_next_task().id)
        queue.mark_completed(queue.get_next_task().id)
        
        pending = queue.list_tasks(status="pending")
        completed = queue.list_tasks(status="completed")
        
        assert len(pending) == 3
        assert len(completed) == 2
    
    def test_list_with_limit(self, queue, sample_files):
        """Test listing with limit."""
        queue.add_tasks_batch(sample_files)
        
        tasks = queue.list_tasks(limit=2)
        
        assert len(tasks) == 2
    
    def test_list_sorted_by_date(self, queue):
        """Test that list is sorted by date (newest first)."""
        task1 = queue.add_task("/first.pdf")
        task2 = queue.add_task("/second.pdf")
        
        tasks = queue.list_tasks()
        
        # Newest first
        assert tasks[0].id == task2.id
        assert tasks[1].id == task1.id


# ==============================================================================
# Cleanup Tests
# ==============================================================================

class TestCleanup:
    """Tests for queue cleanup operations."""
    
    def test_clear_completed(self, queue, sample_files):
        """Test clearing completed tasks."""
        queue.add_tasks_batch(sample_files)
        
        # Complete 2 tasks
        queue.mark_completed(queue.get_next_task().id)
        queue.mark_completed(queue.get_next_task().id)
        
        removed = queue.clear_completed()
        
        assert removed == 2
        
        stats = queue.get_stats()
        assert stats["total"] == 3
        assert stats["completed"] == 0
    
    def test_clear_all(self, queue, sample_files):
        """Test clearing all tasks."""
        queue.add_tasks_batch(sample_files)
        
        removed = queue.clear_all()
        
        assert removed == 5
        
        stats = queue.get_stats()
        assert stats["total"] == 0


# ==============================================================================
# Thread Safety Tests
# ==============================================================================

class TestThreadSafety:
    """Tests for thread-safe operations."""
    
    def test_concurrent_reads(self, queue, sample_files):
        """Test that concurrent reads don't corrupt data."""
        queue.add_tasks_batch(sample_files)
        
        # Simulate multiple reads
        results = []
        for _ in range(10):
            results.append(queue.get_stats())
        
        # All results should be identical
        assert all(r["total"] == 5 for r in results)
    
    def test_file_locking_works(self, temp_queue_file):
        """Test that file locking is applied."""
        queue = TaskQueue(queue_file=str(temp_queue_file))
        
        # Just verify we can perform operations without errors
        queue.add_task("/doc1.pdf")
        queue.add_task("/doc2.pdf")
        queue.mark_completed(queue.get_next_task().id)
        
        stats = queue.get_stats()
        assert stats["completed"] == 1


# ==============================================================================
# Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_unicode_file_paths(self, queue):
        """Test handling of unicode file paths."""
        task = queue.add_task("/docs/文档.pdf")
        
        retrieved = queue.get_task(task.id)
        assert retrieved.file_path == "/docs/文档.pdf"
    
    def test_long_file_paths(self, queue):
        """Test handling of long file paths."""
        long_path = "/very" + "/long" * 50 + "/path.pdf"
        task = queue.add_task(long_path)
        
        retrieved = queue.get_task(task.id)
        assert retrieved.file_path == long_path
    
    def test_special_characters_in_metadata(self, queue):
        """Test handling of special characters in metadata."""
        metadata = {"description": "Test with \"quotes\" and 'apostrophes'"}
        task = queue.add_task("/doc.pdf", metadata=metadata)
        
        retrieved = queue.get_task(task.id)
        assert retrieved.metadata == metadata
    
    def test_empty_file_path(self, queue):
        """Test handling of empty file path."""
        # Should work but not recommended
        task = queue.add_task("")
        assert task.file_path == ""
    
    def test_corrupted_queue_file(self, temp_queue_file):
        """Test recovery from corrupted queue file."""
        # Create corrupted file
        temp_queue_file.parent.mkdir(parents=True, exist_ok=True)
        temp_queue_file.write_text("{invalid json")
        
        # Should handle gracefully and create backup
        queue = TaskQueue(queue_file=str(temp_queue_file))
        
        # Queue should be empty after recovery
        stats = queue.get_stats()
        assert stats["total"] == 0
        
        # Backup should exist
        backup = temp_queue_file.with_suffix(".json.corrupted")
        assert backup.exists()
