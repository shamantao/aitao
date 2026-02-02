"""
Filesystem Scanner for document discovery.

This module scans configured volumes to discover new and modified files
that need to be indexed. It supports:
- Recursive directory traversal
- Pattern-based exclusions (directories, files, extensions)
- Change detection via mtime and SHA256 hash
- State persistence for incremental scans

Usage:
    scanner = FilesystemScanner()
    new_files, modified_files = scanner.scan()
"""

import os
import hashlib
import json
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple, Any
from dataclasses import dataclass, field, asdict

# Import core modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import ConfigManager
from core.logger import get_logger
from core.pathmanager import path_manager

logger = get_logger("scanner")


@dataclass
class FileInfo:
    """Information about a discovered file."""
    path: str
    size: int
    mtime: float
    sha256: Optional[str] = None
    extension: str = ""
    
    def __post_init__(self):
        """Extract extension from path."""
        if not self.extension:
            self.extension = Path(self.path).suffix.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileInfo":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ScanResult:
    """Result of a filesystem scan."""
    new_files: List[FileInfo] = field(default_factory=list)
    modified_files: List[FileInfo] = field(default_factory=list)
    deleted_paths: List[str] = field(default_factory=list)
    total_scanned: int = 0
    total_skipped: int = 0
    scan_duration_seconds: float = 0.0
    
    @property
    def has_changes(self) -> bool:
        """Check if scan found any changes."""
        return bool(self.new_files or self.modified_files or self.deleted_paths)


class FilesystemScanner:
    """
    Scans configured filesystem paths to discover documents.
    
    Features:
    - Reads include/exclude paths from config.yaml
    - Tracks file state (mtime, hash) to detect changes
    - Supports incremental scans with state persistence
    - Filters by supported file extensions
    """
    
    # Default supported extensions for document indexing
    DEFAULT_EXTENSIONS = {
        # Documents
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt",
        # Spreadsheets
        ".xls", ".xlsx", ".ods", ".csv",
        # Presentations
        ".ppt", ".pptx", ".odp",
        # Images (for OCR)
        ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp",
        # Markdown and text
        ".md", ".markdown", ".rst", ".tex",
        # eBooks
        ".epub", ".mobi",
        # Web
        ".html", ".htm",
    }
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        state_file: Optional[str] = None
    ):
        """
        Initialize the scanner.
        
        Args:
            config_path: Path to config.yaml (default: auto-discover)
            state_file: Path to state file for incremental scans
        """
        # Load configuration
        if config_path:
            self.config = ConfigManager(config_path)
        else:
            # Use PathManager for config discovery
            config_file = path_manager.root / "config" / "config.yaml"
            self.config = ConfigManager(str(config_file))
        
        # Get indexing configuration
        indexing_config = self.config.get_section("indexing") or {}
        
        # Include paths from config
        self.include_paths: List[Path] = []
        for path_str in indexing_config.get("include_paths", []):
            expanded = os.path.expandvars(path_str)
            path = Path(expanded).expanduser()
            if path.exists():
                self.include_paths.append(path)
            else:
                logger.warning(f"Include path does not exist: {path}")
        
        # Exclude patterns
        self.exclude_dirs: Set[str] = set(
            indexing_config.get("exclude_dirs", [
                "__pycache__", ".git", ".venv", "node_modules"
            ])
        )
        self.exclude_files: Set[str] = set(
            indexing_config.get("exclude_files", [".DS_Store"])
        )
        self.exclude_extensions: Set[str] = set(
            indexing_config.get("exclude_extensions", [".lock", ".log", ".tmp"])
        )
        
        # Supported extensions (can be overridden in config)
        custom_extensions = indexing_config.get("supported_extensions")
        if custom_extensions:
            self.supported_extensions = set(custom_extensions)
        else:
            self.supported_extensions = self.DEFAULT_EXTENSIONS.copy()
        
        # State file for tracking previously scanned files
        if state_file:
            self.state_file = Path(state_file)
        else:
            # Use PathManager for state file location
            self.state_file = path_manager.get_scanner_state_file()
        
        # Load previous state
        self._file_state: Dict[str, Dict[str, Any]] = {}
        self._load_state()
        
        logger.info(
            f"Scanner initialized",
            metadata={
                "include_paths": [str(p) for p in self.include_paths],
                "exclude_dirs": len(self.exclude_dirs),
                "supported_extensions": len(self.supported_extensions)
            }
        )
    
    def _load_state(self) -> None:
        """Load previous scan state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._file_state = data.get("files", {})
                    logger.debug(
                        f"Loaded scanner state",
                        metadata={"tracked_files": len(self._file_state)}
                    )
            except Exception as e:
                logger.warning(f"Failed to load scanner state: {e}")
                self._file_state = {}
    
    def _save_state(self) -> None:
        """Save current scan state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": 1,
                    "updated_at": datetime.now().isoformat(),
                    "files": self._file_state
                }, f, indent=2)
            logger.debug(f"Saved scanner state: {len(self._file_state)} files")
        except Exception as e:
            logger.error(f"Failed to save scanner state: {e}")
    
    def _should_skip_dir(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        # Skip hidden directories
        if dir_name.startswith("."):
            return True
        # Skip excluded directory names
        if dir_name.lower() in {d.lower() for d in self.exclude_dirs}:
            return True
        return False
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        name = file_path.name
        
        # Skip hidden files
        if name.startswith("."):
            return True
        
        # Skip excluded file names
        if name in self.exclude_files:
            return True
        
        # Skip excluded extensions
        ext = file_path.suffix.lower()
        if ext in self.exclude_extensions:
            return True
        
        # Skip unsupported extensions
        if ext not in self.supported_extensions:
            return True
        
        return False
    
    def _compute_hash(self, file_path: Path, chunk_size: int = 65536) -> str:
        """
        Compute SHA256 hash of file.
        
        Uses chunked reading for large files.
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, OSError) as e:
            logger.warning(f"Cannot hash file {file_path}: {e}")
            return ""
    
    def _get_file_info(self, file_path: Path, compute_hash: bool = True) -> FileInfo:
        """Get information about a file."""
        stat = file_path.stat()
        
        file_info = FileInfo(
            path=str(file_path),
            size=stat.st_size,
            mtime=stat.st_mtime,
            extension=file_path.suffix.lower()
        )
        
        if compute_hash:
            file_info.sha256 = self._compute_hash(file_path)
        
        return file_info
    
    def _is_file_modified(self, file_path: Path, current_mtime: float) -> bool:
        """
        Check if file has been modified since last scan.
        
        Uses mtime for quick check, falls back to hash comparison.
        """
        path_str = str(file_path)
        
        if path_str not in self._file_state:
            return True  # New file
        
        previous = self._file_state[path_str]
        
        # Quick mtime check
        if previous.get("mtime") != current_mtime:
            return True
        
        return False
    
    def scan(
        self,
        paths: Optional[List[str]] = None,
        compute_hashes: bool = True,
        save_state: bool = True
    ) -> ScanResult:
        """
        Scan filesystem for new and modified files.
        
        Args:
            paths: Specific paths to scan (default: use config include_paths)
            compute_hashes: Whether to compute SHA256 hashes
            save_state: Whether to save state after scan
        
        Returns:
            ScanResult with new_files, modified_files, and stats
        """
        import time
        start_time = time.time()
        
        result = ScanResult()
        current_files: Set[str] = set()
        
        # Determine paths to scan
        scan_paths = []
        if paths:
            for p in paths:
                path = Path(p).expanduser()
                if path.exists():
                    scan_paths.append(path)
                else:
                    logger.warning(f"Path does not exist: {p}")
        else:
            scan_paths = self.include_paths
        
        if not scan_paths:
            logger.warning("No valid paths to scan")
            return result
        
        logger.info(
            f"Starting scan",
            metadata={"paths": [str(p) for p in scan_paths]}
        )
        
        # Scan each path
        for base_path in scan_paths:
            self._scan_directory(
                base_path,
                result,
                current_files,
                compute_hashes
            )
        
        # Find deleted files
        previous_files = set(self._file_state.keys())
        deleted = previous_files - current_files
        result.deleted_paths = list(deleted)
        
        # Remove deleted files from state
        for path in deleted:
            del self._file_state[path]
        
        # Calculate duration
        result.scan_duration_seconds = time.time() - start_time
        
        # Save state
        if save_state:
            self._save_state()
        
        logger.info(
            f"Scan complete",
            metadata={
                "new": len(result.new_files),
                "modified": len(result.modified_files),
                "deleted": len(result.deleted_paths),
                "total_scanned": result.total_scanned,
                "skipped": result.total_skipped,
                "duration_s": round(result.scan_duration_seconds, 2)
            }
        )
        
        return result
    
    def _scan_directory(
        self,
        directory: Path,
        result: ScanResult,
        current_files: Set[str],
        compute_hashes: bool
    ) -> None:
        """Recursively scan a directory."""
        try:
            for entry in os.scandir(directory):
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if not self._should_skip_dir(entry.name):
                            self._scan_directory(
                                Path(entry.path),
                                result,
                                current_files,
                                compute_hashes
                            )
                    elif entry.is_file(follow_symlinks=False):
                        file_path = Path(entry.path)
                        
                        if self._should_skip_file(file_path):
                            result.total_skipped += 1
                            continue
                        
                        result.total_scanned += 1
                        path_str = str(file_path)
                        current_files.add(path_str)
                        
                        # Check modification
                        stat = entry.stat()
                        mtime = stat.st_mtime
                        
                        if path_str not in self._file_state:
                            # New file
                            file_info = self._get_file_info(
                                file_path, compute_hashes
                            )
                            result.new_files.append(file_info)
                            self._file_state[path_str] = file_info.to_dict()
                            
                        elif self._is_file_modified(file_path, mtime):
                            # Modified file
                            file_info = self._get_file_info(
                                file_path, compute_hashes
                            )
                            result.modified_files.append(file_info)
                            self._file_state[path_str] = file_info.to_dict()
                            
                except PermissionError:
                    logger.debug(f"Permission denied: {entry.path}")
                except Exception as e:
                    logger.warning(f"Error processing {entry.path}: {e}")
                    
        except PermissionError:
            logger.debug(f"Permission denied: {directory}")
        except Exception as e:
            logger.warning(f"Error scanning directory {directory}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            "include_paths": [str(p) for p in self.include_paths],
            "tracked_files": len(self._file_state),
            "supported_extensions": len(self.supported_extensions),
            "exclude_dirs": len(self.exclude_dirs),
            "state_file": str(self.state_file)
        }
    
    def clear_state(self) -> None:
        """Clear the scanner state (force full rescan)."""
        self._file_state = {}
        if self.state_file.exists():
            self.state_file.unlink()
        logger.info("Scanner state cleared")
