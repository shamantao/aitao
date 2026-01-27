#!/usr/bin/env python3
"""
Failed Files Tracker - AI Tao

Tracks files that failed to index for potential retry.
Stores failed files in a JSON file with error details.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import hashlib

try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
except ImportError:
    from core.path_manager import path_manager
    from core.logger import get_logger

logger = get_logger("FailedFilesTracker", "failed_files.log")


class FailedFilesTracker:
    """Track files that failed to index for potential retry."""
    
    def __init__(self):
        """Initialize tracker with storage path."""
        storage_root = path_manager.get_storage_root()
        self.failed_files_path = storage_root / "failed_files.json"
        self._failed_files = self._load()

    def _compute_sha256(self, file_path: str) -> str:
        """Compute SHA256 hash of a file."""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to compute SHA256 for {file_path}: {e}")
            return ""
    
    def _load(self) -> Dict:
        """Load failed files from disk."""
        if not self.failed_files_path.exists():
            return {}
        
        try:
            with open(self.failed_files_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load failed_files.json: {e}")
            return {}
    
    def _save(self):
        """Save failed files to disk."""
        try:
            os.makedirs(self.failed_files_path.parent, exist_ok=True)
            with open(self.failed_files_path, "w", encoding="utf-8") as f:
                json.dump(self._failed_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save failed_files.json: {e}")
    
    def add_failed_file(self, file_path: str, error: str, reason: str = "unknown"):
        """Add a file that failed to index.
        
        Args:
            file_path: Path to the file
            error: Error message
            reason: Reason category (encoding, empty, parse_error, etc.)
        """
        file_size = 0
        sha256 = ""

        try:
            file_size = os.path.getsize(file_path)
            sha256 = self._compute_sha256(file_path)
        except Exception as e:
            logger.warning(f"Failed to get file info for {file_path}: {e}")

        self._failed_files[file_path] = {
            "error": str(error),
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "retry_count": self._failed_files.get(file_path, {}).get("retry_count", 0),
            "file_size": file_size,
            "sha256": sha256
        }
        self._save()
    
    def mark_success(self, file_path: str):
        """Remove a file from failed list after successful indexing."""
        if file_path in self._failed_files:
            del self._failed_files[file_path]
            self._save()
    
    def increment_retry(self, file_path: str):
        """Increment retry count for a failed file."""
        if file_path in self._failed_files:
            self._failed_files[file_path]["retry_count"] += 1
            self._failed_files[file_path]["last_retry"] = datetime.now().isoformat()
            self._save()
    
    def get_failed_files(self, max_retries: int = 3) -> List[str]:
        """Get list of failed files that haven't exceeded max retries.
        
        Args:
            max_retries: Maximum retry attempts
            
        Returns:
            List of file paths to retry
        """
        return [
            path for path, info in self._failed_files.items()
            if info.get("retry_count", 0) < max_retries
        ]
    
    def get_stats(self) -> Dict:
        """Get statistics about failed files."""
        total = len(self._failed_files)
        by_reason = {}
        
        for info in self._failed_files.values():
            reason = info.get("reason", "unknown")
            by_reason[reason] = by_reason.get(reason, 0) + 1
        
        return {
            "total_failed": total,
            "by_reason": by_reason,
            "retryable": len(self.get_failed_files())
        }
    
    def clear_old_failures(self, days: int = 30):
        """Clear failures older than specified days.
        
        Args:
            days: Number of days to keep failures
        """
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        old_count = len(self._failed_files)
        self._failed_files = {
            path: info for path, info in self._failed_files.items()
            if info.get("timestamp", "") > cutoff
        }
        
        removed = old_count - len(self._failed_files)
        if removed > 0:
            self._save()
            logger.info(f"Cleared {removed} old failed file entries")


__all__ = ["FailedFilesTracker"]
