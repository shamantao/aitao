"""
Task Queue for asynchronous document processing.

This module provides a file-based queue system for managing indexation tasks.
Features:
- JSON-based persistence
- Thread-safe file locking
- Priority-based task ordering
- Task state management (pending, processing, completed, failed)

Usage:
    queue = TaskQueue()
    queue.add_task("/path/to/doc.pdf", task_type="index")
    task = queue.get_next_task()
    queue.update_status(task.id, "completed")
"""

import os
import json
import uuid
import fcntl
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

# Import core modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import ConfigManager, get_config
from core.logger import get_logger


def _get_logger():
    """Get logger lazily to respect AITAO_QUIET env var."""
    return get_logger("queue")


class TaskPriority(str, Enum):
    """Task priority levels."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    
    @property
    def sort_order(self) -> int:
        """Return numeric value for sorting (lower = higher priority)."""
        return {"high": 0, "normal": 1, "low": 2}[self.value]


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of tasks the queue can handle."""
    INDEX = "index"           # Full indexation (text extraction + embedding)
    OCR = "ocr"              # OCR for images/scanned PDFs
    TRANSLATE = "translate"   # Translation task
    REINDEX = "reindex"      # Re-index existing document
    DELETE = "delete"        # Remove from index


@dataclass
class Task:
    """Represents a task in the queue."""
    id: str
    file_path: str
    task_type: str
    priority: str = TaskPriority.NORMAL.value
    status: str = TaskStatus.PENDING.value
    added_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default values."""
        if not self.added_at:
            self.added_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(**data)
    
    @property
    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status == TaskStatus.PENDING.value
    
    @property
    def is_processing(self) -> bool:
        """Check if task is being processed."""
        return self.status == TaskStatus.PROCESSING.value


class TaskQueue:
    """
    File-based task queue with JSON persistence.
    
    Thread-safe through file locking (fcntl).
    Tasks are ordered by priority, then by added_at timestamp.
    """
    
    MAX_RETRIES = 3
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        queue_file: Optional[str] = None
    ):
        """
        Initialize the task queue.
        
        Args:
            config_path: Path to config.yaml
            queue_file: Custom path to queue file
        """
        # Load configuration (use global singleton for consistent paths)
        if config_path:
            self.config = ConfigManager(config_path)
        else:
            try:
                self.config = get_config()
            except Exception:
                self.config = None
        
        # Determine queue file location
        if queue_file:
            self.queue_file = Path(queue_file)
        elif self.config:
            queue_dir = self.config.get("paths.queue_dir")
            if queue_dir:
                queue_path = Path(os.path.expandvars(queue_dir)).expanduser()
            else:
                # Fallback to storage_root/queue if queue_dir not set
                storage_root = self.config.get("paths.storage_root")
                if storage_root:
                    queue_path = Path(storage_root) / "queue"
                else:
                    raise ValueError("No queue_dir or storage_root configured")
            self.queue_file = queue_path / "tasks.json"
        else:
            raise ValueError("No configuration available for queue path")
        
        # Ensure directory exists
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty queue if file doesn't exist
        if not self.queue_file.exists():
            self._save_tasks([])
        
        _get_logger().info(
            f"TaskQueue initialized",
            metadata={"queue_file": str(self.queue_file)}
        )
    
    def _load_tasks(self) -> List[Task]:
        """Load tasks from JSON file with file locking."""
        tasks = []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                try:
                    data = json.load(f)
                    tasks = [Task.from_dict(t) for t in data]
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as e:
            _get_logger().error(f"Corrupted queue file: {e}")
            # Backup corrupted file and start fresh
            backup = self.queue_file.with_suffix(".json.corrupted")
            self.queue_file.rename(backup)
            _get_logger().warning(f"Backed up corrupted queue to {backup}")
        return tasks
    
    def _save_tasks(self, tasks: List[Task]) -> None:
        """Save tasks to JSON file with file locking."""
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                try:
                    data = [t.to_dict() for t in tasks]
                    json.dump(data, f, indent=2, ensure_ascii=False)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            _get_logger().error(f"Failed to save queue: {e}")
            raise
    
    def _with_lock(self, operation):
        """Execute operation with exclusive file lock."""
        tasks = self._load_tasks()
        result = operation(tasks)
        self._save_tasks(tasks)
        return result
    
    def add_task(
        self,
        file_path: str,
        task_type: str = TaskType.INDEX.value,
        priority: str = TaskPriority.NORMAL.value,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Add a new task to the queue.
        
        Args:
            file_path: Path to the file to process
            task_type: Type of task (index, ocr, translate, etc.)
            priority: Priority level (high, normal, low)
            metadata: Additional task metadata
        
        Returns:
            The created Task object
        """
        task = Task(
            id=str(uuid.uuid4())[:8],  # Short UUID
            file_path=file_path,
            task_type=task_type,
            priority=priority,
            metadata=metadata or {}
        )
        
        tasks = self._load_tasks()
        
        # Check for duplicate (same file, same type, pending)
        for existing in tasks:
            if (existing.file_path == file_path and 
                existing.task_type == task_type and
                existing.status == TaskStatus.PENDING.value):
                _get_logger().debug(f"Task already exists for {file_path}")
                return existing
        
        tasks.append(task)
        self._save_tasks(tasks)
        
        _get_logger().info(
            f"Task added",
            metadata={
                "task_id": task.id,
                "file": Path(file_path).name,
                "type": task_type,
                "priority": priority
            }
        )
        
        return task
    
    def add_tasks_batch(
        self,
        file_paths: List[str],
        task_type: str = TaskType.INDEX.value,
        priority: str = TaskPriority.NORMAL.value
    ) -> List[Task]:
        """
        Add multiple tasks efficiently.
        
        Args:
            file_paths: List of file paths
            task_type: Type of task
            priority: Priority level
        
        Returns:
            List of created Task objects
        """
        tasks = self._load_tasks()
        existing_paths = {
            t.file_path for t in tasks 
            if t.task_type == task_type and t.status == TaskStatus.PENDING.value
        }
        
        new_tasks = []
        for file_path in file_paths:
            if file_path not in existing_paths:
                task = Task(
                    id=str(uuid.uuid4())[:8],
                    file_path=file_path,
                    task_type=task_type,
                    priority=priority
                )
                tasks.append(task)
                new_tasks.append(task)
        
        if new_tasks:
            self._save_tasks(tasks)
            _get_logger().info(f"Added {len(new_tasks)} tasks to queue")
        
        return new_tasks
    
    def get_next_task(self) -> Optional[Task]:
        """
        Get the next pending task to process.
        
        Returns tasks ordered by:
        1. Priority (high → normal → low)
        2. Added timestamp (oldest first)
        
        Returns:
            Next pending Task or None if queue is empty
        """
        tasks = self._load_tasks()
        
        # Filter pending tasks
        pending = [t for t in tasks if t.status == TaskStatus.PENDING.value]
        
        if not pending:
            return None
        
        # Sort by priority, then by timestamp
        pending.sort(key=lambda t: (
            TaskPriority(t.priority).sort_order,
            t.added_at
        ))
        
        return pending[0]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        tasks = self._load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_status(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            error_message: Error message (for failed status)
        
        Returns:
            True if task was updated, False if not found
        """
        tasks = self._load_tasks()
        
        for task in tasks:
            if task.id == task_id:
                task.status = status
                
                if status == TaskStatus.PROCESSING.value:
                    task.started_at = datetime.now().isoformat()
                elif status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
                    task.completed_at = datetime.now().isoformat()
                
                if error_message:
                    task.error_message = error_message
                    task.retry_count += 1
                
                self._save_tasks(tasks)
                
                _get_logger().info(
                    f"Task status updated",
                    metadata={
                        "task_id": task_id,
                        "status": status,
                        "error": error_message
                    }
                )
                return True
        
        return False
    
    def mark_processing(self, task_id: str) -> bool:
        """Mark task as processing."""
        return self.update_status(task_id, TaskStatus.PROCESSING.value)
    
    def mark_completed(self, task_id: str) -> bool:
        """Mark task as completed."""
        return self.update_status(task_id, TaskStatus.COMPLETED.value)
    
    def mark_failed(self, task_id: str, error: str) -> bool:
        """Mark task as failed with error message."""
        return self.update_status(task_id, TaskStatus.FAILED.value, error)
    
    def retry_failed(self) -> int:
        """
        Retry failed tasks that haven't exceeded max retries.
        
        Returns:
            Number of tasks reset to pending
        """
        tasks = self._load_tasks()
        retry_count = 0
        
        for task in tasks:
            if (task.status == TaskStatus.FAILED.value and 
                task.retry_count < self.MAX_RETRIES):
                task.status = TaskStatus.PENDING.value
                task.error_message = None
                retry_count += 1
        
        if retry_count > 0:
            self._save_tasks(tasks)
            _get_logger().info(f"Reset {retry_count} failed tasks to pending")
        
        return retry_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        tasks = self._load_tasks()
        
        stats = {
            "total": len(tasks),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "by_type": {},
            "by_priority": {"high": 0, "normal": 0, "low": 0}
        }
        
        for task in tasks:
            # Count by status
            if task.status == TaskStatus.PENDING.value:
                stats["pending"] += 1
            elif task.status == TaskStatus.PROCESSING.value:
                stats["processing"] += 1
            elif task.status == TaskStatus.COMPLETED.value:
                stats["completed"] += 1
            elif task.status == TaskStatus.FAILED.value:
                stats["failed"] += 1
            
            # Count by type
            stats["by_type"][task.task_type] = stats["by_type"].get(task.task_type, 0) + 1
            
            # Count by priority (only pending)
            if task.status == TaskStatus.PENDING.value:
                stats["by_priority"][task.priority] = stats["by_priority"].get(task.priority, 0) + 1
        
        return stats
    
    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Task]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Filter by status (or None for all)
            limit: Maximum number of tasks to return
        
        Returns:
            List of Task objects
        """
        tasks = self._load_tasks()
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by added_at descending (newest first)
        tasks.sort(key=lambda t: t.added_at, reverse=True)
        
        return tasks[:limit]
    
    def clear_completed(self) -> int:
        """
        Remove completed tasks from the queue.
        
        Returns:
            Number of tasks removed
        """
        tasks = self._load_tasks()
        original_count = len(tasks)
        
        tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED.value]
        
        removed = original_count - len(tasks)
        if removed > 0:
            self._save_tasks(tasks)
            _get_logger().info(f"Cleared {removed} completed tasks")
        
        return removed
    
    def reset_stuck_tasks(self, timeout_seconds: int = 600) -> int:
        """
        Reset tasks stuck in 'processing' status back to 'pending'.
        
        Tasks are considered stuck if they have been in 'processing' status
        for longer than timeout_seconds. This handles cases where the worker
        crashed without properly completing or failing the task.
        
        Args:
            timeout_seconds: Time in seconds after which a processing task
                           is considered stuck (default: 600 = 10 minutes)
        
        Returns:
            Number of tasks reset
        """
        from datetime import datetime, timezone
        
        tasks = self._load_tasks()
        now = datetime.now(timezone.utc)
        reset_count = 0
        
        for task in tasks:
            if task.status != TaskStatus.PROCESSING.value:
                continue
            
            if not task.started_at:
                # No start time, definitely stuck
                task.status = TaskStatus.PENDING.value
                task.started_at = None
                reset_count += 1
                continue
            
            # Parse started_at and check age
            try:
                # Handle various ISO formats
                started_str = task.started_at.replace('Z', '+00:00')
                if '+' not in started_str and '-' not in started_str[-6:]:
                    # No timezone, assume UTC
                    started = datetime.fromisoformat(started_str).replace(tzinfo=timezone.utc)
                else:
                    started = datetime.fromisoformat(started_str)
                
                age_seconds = (now - started).total_seconds()
                
                if age_seconds > timeout_seconds:
                    _get_logger().warning(
                        f"Resetting stuck task",
                        metadata={
                            "task_id": task.id,
                            "file": task.file_path,
                            "stuck_for_seconds": int(age_seconds)
                        }
                    )
                    task.status = TaskStatus.PENDING.value
                    task.started_at = None
                    reset_count += 1
                    
            except (ValueError, TypeError) as e:
                # Can't parse date, reset to be safe
                _get_logger().warning(f"Cannot parse started_at for task {task.id}: {e}")
                task.status = TaskStatus.PENDING.value
                task.started_at = None
                reset_count += 1
        
        if reset_count > 0:
            self._save_tasks(tasks)
            _get_logger().info(f"Reset {reset_count} stuck tasks to pending")
        
        return reset_count
    
    def clear_all(self) -> int:
        """
        Remove all tasks from the queue.
        
        Returns:
            Number of tasks removed
        """
        tasks = self._load_tasks()
        count = len(tasks)
        
        self._save_tasks([])
        _get_logger().info(f"Cleared all {count} tasks from queue")
        
        return count
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        return self.update_status(task_id, TaskStatus.CANCELLED.value)
