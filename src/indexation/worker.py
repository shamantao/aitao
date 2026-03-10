"""
Background Worker for document processing.

This module provides a background worker that processes tasks from the queue.
Features:
- Configurable poll interval (default: 30 seconds)
- System load monitoring (CPU threshold)
- Sequential task processing
- PID file for daemon management
- Graceful shutdown on SIGTERM/SIGINT

Usage:
    worker = BackgroundWorker()
    worker.run()  # Blocking loop
    
    # Or as daemon:
    worker.start_daemon()
    worker.stop_daemon()
"""

import os
import sys
import time
import signal
import psutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

# Import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import ConfigManager
from core.logger import get_logger
from src.indexation.queue import TaskQueue, Task, TaskStatus
from src.indexation.indexer import DocumentIndexer
from src.indexation.scanner import FilesystemScanner


def _get_logger():
    """Get logger lazily to respect AITAO_QUIET env var."""
    return get_logger("worker")


@dataclass
class WorkerConfig:
    """Worker configuration settings."""
    poll_interval: int = 5           # Seconds between queue polls (default: 5s)
    cpu_threshold: float = 80.0      # Max CPU % before pausing
    max_consecutive_errors: int = 5  # Errors before pause
    error_pause_time: int = 60       # Seconds to pause after errors
    shutdown_timeout: int = 30       # Seconds to wait for graceful shutdown
    stuck_task_timeout: int = 600    # Seconds before a processing task is considered stuck (10 min)


@dataclass
class WorkerStats:
    """Worker runtime statistics."""
    started_at: Optional[str] = None
    tasks_processed: int = 0
    tasks_failed: int = 0
    last_poll: Optional[str] = None
    last_task_id: Optional[str] = None
    consecutive_errors: int = 0
    is_running: bool = False
    is_paused: bool = False
    pause_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "started_at": self.started_at,
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "last_poll": self.last_poll,
            "last_task_id": self.last_task_id,
            "consecutive_errors": self.consecutive_errors,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "pause_reason": self.pause_reason
        }


class BackgroundWorker:
    """
    Background worker that processes tasks from the queue.
    
    The worker polls the queue at regular intervals and processes
    tasks one at a time. It monitors system load and pauses if
    CPU usage is too high.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        queue: Optional[TaskQueue] = None,
        task_handler: Optional[Callable[[Task], bool]] = None
    ):
        """
        Initialize the background worker.
        
        Args:
            config_path: Path to config.toml
            queue: Optional TaskQueue instance (creates one if not provided)
            task_handler: Optional callback to process tasks
        """
        # Load configuration
        if config_path:
            self.config_manager = ConfigManager(config_path)
        else:
            project_root = Path(__file__).parent.parent.parent
            config_file = project_root / "config" / "config.toml"
            if config_file.exists():
                self.config_manager = ConfigManager(str(config_file))
            else:
                self.config_manager = None
        
        # Worker configuration
        self.worker_config = WorkerConfig()
        if self.config_manager:
            worker_section = self.config_manager.get("worker", {})
            if isinstance(worker_section, dict):
                self.worker_config.poll_interval = worker_section.get(
                    "poll_interval", 5
                )
                self.worker_config.cpu_threshold = worker_section.get(
                    "cpu_threshold", 80.0
                )
                self.worker_config.stuck_task_timeout = worker_section.get(
                    "stuck_task_timeout", 600
                )
        
        # Initialize queue
        self.queue = queue or TaskQueue(config_path=config_path)
        
        # Task handler (will be replaced by DocumentIndexer in US-012)
        self.task_handler = task_handler or self._default_handler
        
        # Runtime state
        self.stats = WorkerStats()
        self._shutdown_requested = False
        
        # PID file path
        if self.config_manager:
            storage_root = self.config_manager.get("paths.storage_root")
            if storage_root:
                storage_path = Path(os.path.expandvars(storage_root)).expanduser()
            else:
                raise ValueError("storage_root not configured - check config.toml")
        else:
            raise ValueError("ConfigManager required for worker initialization")
        self.pid_file = storage_path / "worker.pid"
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
        _get_logger().info(
            "BackgroundWorker initialized",
            metadata={
                "poll_interval": self.worker_config.poll_interval,
                "cpu_threshold": self.worker_config.cpu_threshold,
                "pid_file": str(self.pid_file)
            }
        )
    
    def _default_handler(self, task: Task) -> bool:
        """
        Default task handler that indexes documents.
        
        Calls DocumentIndexer to:
        1. Extract text from the file
        2. Generate embeddings
        3. Index in LanceDB + Meilisearch
        
        Args:
            task: Task to process
        
        Returns:
            True if successful, False otherwise
        """
        _get_logger().info(
            f"Processing task",
            metadata={
                "task_id": task.id,
                "file_path": task.file_path,
                "task_type": task.task_type
            }
        )
        
        try:
            # Create indexer and index the document
            indexer = DocumentIndexer()
            result = indexer.index_file(task.file_path)
            
            if result.success:
                _get_logger().info(
                    f"Document indexed successfully",
                    metadata={
                        "task_id": task.id,
                        "doc_id": result.doc_id,
                        "word_count": result.word_count
                    }
                )
                return True
            else:
                _get_logger().error(
                    f"Document indexing failed",
                    metadata={
                        "task_id": task.id,
                        "error": result.error
                    }
                )
                return False
                
        except Exception as e:
            _get_logger().error(
                f"Exception during indexing",
                metadata={
                    "task_id": task.id,
                    "error": str(e)
                }
            )
            return False
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        _get_logger().info(f"Shutdown signal received ({signum})")
        self._shutdown_requested = True
    
    def _check_system_load(self) -> tuple[bool, str]:
        """
        Check if system load allows task processing.
        
        Returns:
            Tuple of (can_process, reason)
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent >= self.worker_config.cpu_threshold:
                return False, f"CPU usage too high: {cpu_percent:.1f}%"
            
            return True, ""
        except Exception as e:
            _get_logger().warning(f"Failed to check system load: {e}")
            return True, ""  # Continue if we can't check
    
    def _write_pid_file(self):
        """Write PID file for daemon management."""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()))
        _get_logger().debug(f"PID file written: {self.pid_file}")
    
    def _remove_pid_file(self):
        """Remove PID file on shutdown."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                _get_logger().debug(f"PID file removed: {self.pid_file}")
        except Exception as e:
            _get_logger().warning(f"Failed to remove PID file: {e}")
    
    def _process_task(self, task: Task) -> bool:
        """
        Process a single task.
        
        Args:
            task: Task to process
        
        Returns:
            True if successful, False otherwise
        """
        self.stats.last_task_id = task.id
        
        # Mark as processing
        self.queue.mark_processing(task.id)
        
        _get_logger().info(
            f"Starting task",
            metadata={
                "task_id": task.id,
                "file": Path(task.file_path).name,
                "type": task.task_type
            }
        )
        
        try:
            # Call the task handler
            success = self.task_handler(task)
            
            if success:
                self.queue.mark_completed(task.id)
                self.stats.tasks_processed += 1
                self.stats.consecutive_errors = 0
                
                _get_logger().info(
                    f"Task completed",
                    metadata={"task_id": task.id}
                )
                return True
            else:
                raise Exception("Task handler returned False")
            
        except Exception as e:
            self.queue.mark_failed(task.id, str(e))
            self.stats.tasks_failed += 1
            self.stats.consecutive_errors += 1
            
            _get_logger().error(
                f"Task failed",
                metadata={
                    "task_id": task.id,
                    "error": str(e)
                }
            )
            return False
    
    def _reset_stuck_tasks(self) -> int:
        """
        Reset tasks that are stuck in 'processing' status.
        
        This handles recovery from worker crashes where tasks were
        marked as processing but never completed.
        
        Returns:
            Number of tasks reset
        """
        try:
            reset_count = self.queue.reset_stuck_tasks(
                timeout_seconds=self.worker_config.stuck_task_timeout
            )
            if reset_count > 0:
                _get_logger().info(
                    f"Reset {reset_count} stuck tasks at startup/check"
                )
            return reset_count
        except Exception as e:
            _get_logger().error(f"Error resetting stuck tasks: {e}")
            return 0
    
    def _poll_and_process(self) -> bool:
        """
        Poll queue and process one task.
        
        Returns:
            True if a task was processed, False otherwise
        """
        self.stats.last_poll = datetime.now().isoformat()
        
        # Check system load
        can_process, reason = self._check_system_load()
        if not can_process:
            self.stats.is_paused = True
            self.stats.pause_reason = reason
            _get_logger().warning(f"Pausing: {reason}")
            return False
        
        self.stats.is_paused = False
        self.stats.pause_reason = None
        
        # Check for too many consecutive errors
        if self.stats.consecutive_errors >= self.worker_config.max_consecutive_errors:
            _get_logger().warning(
                f"Too many consecutive errors ({self.stats.consecutive_errors}), "
                f"pausing for {self.worker_config.error_pause_time}s"
            )
            time.sleep(self.worker_config.error_pause_time)
            self.stats.consecutive_errors = 0
        
        # Get next task
        task = self.queue.get_next_task()
        
        if task is None:
            _get_logger().debug("No pending tasks")
            return False
        
        # Process the task
        return self._process_task(task)
    
    def run(self) -> None:
        """
        Run the worker in blocking mode.
        
        Polls the queue at regular intervals until shutdown is requested.
        """
        _get_logger().info("Worker starting...")
        
        self._write_pid_file()
        self.stats.is_running = True
        self.stats.started_at = datetime.now().isoformat()
        
        # Reset any stuck tasks from previous crash
        self._reset_stuck_tasks()
        
        # Counter for periodic stuck task check
        polls_since_stuck_check = 0
        stuck_check_interval = 10  # Check every 10 polls (~5 minutes)

        scanner = FilesystemScanner()
        indexing_config = self.config_manager.get_section("indexing") if self.config_manager else {}
        scan_interval_minutes = indexing_config.get("interval_minutes", 10) if indexing_config else 10
        scan_interval_seconds = scan_interval_minutes * 60
        last_scan_time = 0
        
        try:
            while not self._shutdown_requested:
                try:
                    current_time = time.time()
                    if current_time - last_scan_time >= scan_interval_seconds:
                        _get_logger().info("Starting periodic filesystem scan...")
                        scan_result = scanner.scan()
                        
                        if scan_result.has_changes:
                            files_to_index = scan_result.new_files + scan_result.modified_files
                            for file_info in files_to_index:
                                self.queue.add_task(str(file_info.path), task_type="index")
                            
                            _get_logger().info(
                                "Scan complete",
                                metadata={
                                    "new": len(scan_result.new_files),
                                    "modified": len(scan_result.modified_files),
                                    "skipped": scan_result.total_skipped,
                                    "deleted": len(scan_result.deleted_paths)
                                }
                            )
                        else:
                            _get_logger().info(
                                "Scan complete: no changes detected",
                                metadata={"skipped": scan_result.total_skipped}
                            )
                        
                        last_scan_time = current_time
                    
                    self._poll_and_process()
                    
                    # Periodically check for stuck tasks
                    polls_since_stuck_check += 1
                    if polls_since_stuck_check >= stuck_check_interval:
                        self._reset_stuck_tasks()
                        polls_since_stuck_check = 0
                        
                except Exception as e:
                    _get_logger().error(f"Error in poll loop: {e}")
                
                # Sleep in small increments to allow quick shutdown
                for _ in range(self.worker_config.poll_interval):
                    if self._shutdown_requested:
                        break
                    time.sleep(1)
            
            _get_logger().info("Worker shutting down gracefully...")
            
        finally:
            self.stats.is_running = False
            self._remove_pid_file()
            _get_logger().info(
                "Worker stopped",
                metadata={
                    "tasks_processed": self.stats.tasks_processed,
                    "tasks_failed": self.stats.tasks_failed
                }
            )
    
    def run_once(self) -> bool:
        """
        Process one task and return.
        
        Useful for testing or manual processing.
        
        Returns:
            True if a task was processed, False otherwise
        """
        return self._poll_and_process()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return self.stats.to_dict()
    
    # -------------------------------------------------------------------------
    # Daemon Management
    # -------------------------------------------------------------------------
    
    def is_running(self) -> bool:
        """Check if worker daemon is running."""
        if not self.pid_file.exists():
            return False
        
        try:
            pid = int(self.pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False
    
    def get_pid(self) -> Optional[int]:
        """Get worker PID if running."""
        if not self.pid_file.exists():
            return None
        
        try:
            return int(self.pid_file.read_text().strip())
        except ValueError:
            return None
    
    def start_daemon(self) -> bool:
        """
        Start the worker as a background daemon using subprocess.
        
        Uses subprocess.Popen instead of os.fork() for macOS Metal compatibility.
        The fork() system call is not safe with Metal/MPS GPU libraries.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            _get_logger().warning("Worker already running")
            return False
        
        # Use subprocess instead of fork for Metal/MPS compatibility
        # Find project root to run the worker script
        project_root = Path(__file__).parent.parent.parent
        python_exe = sys.executable
        worker_script = project_root / "scripts" / "run_worker.py"
        
        # Use dedicated worker script (avoids inline import issues)
        worker_cmd = [python_exe, str(worker_script)]
        
        try:
            # Start worker as detached subprocess
            process = subprocess.Popen(
                worker_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent
                cwd=str(project_root),
            )
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Check if it started successfully
            if process.poll() is None:
                _get_logger().info(f"Worker started with PID {process.pid}")
                return True
            else:
                _get_logger().error("Worker failed to start")
                return False
                
        except Exception as e:
            _get_logger().error(f"Failed to start worker: {e}")
            return False
    
    def stop_daemon(self, timeout: int = 10) -> bool:
        """
        Stop the running daemon.
        
        Args:
            timeout: Seconds to wait for graceful shutdown
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pid = self.get_pid()
        
        if pid is None:
            _get_logger().info("Worker not running")
            return True
        
        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to terminate
            for _ in range(timeout):
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    _get_logger().info("Worker stopped")
                    self._remove_pid_file()
                    return True
            
            # Force kill if still running
            _get_logger().warning("Worker not responding, forcing kill")
            os.kill(pid, signal.SIGKILL)
            self._remove_pid_file()
            return True
            
        except ProcessLookupError:
            _get_logger().info("Worker already stopped")
            self._remove_pid_file()
            return True
        except PermissionError:
            _get_logger().error("Permission denied to stop worker")
            return False
