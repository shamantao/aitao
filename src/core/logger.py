"""
Core logging module with structured JSON output.

This module provides a centralized logger with:
- JSON structured format for easy parsing and monitoring
- Automatic log rotation (100MB max per file)
- Separate log files per module
- Context metadata support
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
"""

import sys
import logging
import json
import tempfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from pathlib import Path


def _temp_logs_dir() -> Path:
    """Return a safe temp directory for logs when PathManager is unavailable."""
    path = Path(tempfile.gettempdir()) / "aitao_logs"
    path.mkdir(exist_ok=True)
    return path


# Import PathManager
try:
    from src.core.pathmanager import path_manager
except ImportError:
    try:
        from core.pathmanager import path_manager
    except ImportError:
        # Emergency fallback: write to system temp dir, never to CWD
        class FallbackPathManager:
            def get_logs_dir(self):
                return _temp_logs_dir()
        path_manager = FallbackPathManager()


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format.
    
    Output format:
    {
        "timestamp": "2026-01-28T14:30:45.123Z",
        "level": "INFO",
        "module": "indexer",
        "message": "File indexed successfully",
        "metadata": {"file_path": "/path/to/file.pdf", "duration_ms": 123}
    }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        
        # Add metadata if present
        if hasattr(record, 'metadata') and record.metadata:
            log_data["metadata"] = record.metadata
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=self._json_safe)


    def _json_safe(self, obj):
        """Convert non-serializable objects to strings for JSON logging."""
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console output.
    
    Format: 2026-01-28 14:30:45 [INFO] [indexer] File indexed successfully
    """
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class StructuredLogger:
    """
    Wrapper around Python's logging.Logger with structured logging support.
    
    Usage:
        logger = get_logger("indexer")
        logger.info("File indexed", metadata={"file": "doc.pdf", "pages": 5})
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _log(self, level: int, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Internal log method with metadata support."""
        extra = {'metadata': metadata} if metadata else {}
        self._logger.log(level, message, extra=extra)
    
    def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self._log(logging.DEBUG, message, metadata)
    
    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self._log(logging.INFO, message, metadata)
    
    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self._log(logging.WARNING, message, metadata)
    
    def error(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log error message."""
        self._log(logging.ERROR, message, metadata)
    
    def critical(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log critical message."""
        self._log(logging.CRITICAL, message, metadata)
    
    def exception(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log exception with traceback."""
        extra = {'metadata': metadata} if metadata else {}
        self._logger.exception(message, extra=extra)


# Module-level logger cache to avoid recreating loggers
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(
    name: str, 
    log_filename: Optional[str] = None,
    level: int = logging.INFO
) -> StructuredLogger:
    """
    Get a configured structured logger for a module.
    
    Args:
        name: Logger name (e.g., 'indexer', 'ocr', 'api')
        log_filename: Custom log filename. If None, derives from name.
                     Example: 'indexer.log', 'ocr.log', 'api.log'
        level: Logging level (default: INFO)
    
    Returns:
        StructuredLogger instance with file and console handlers
    
    Example:
        >>> logger = get_logger("indexer")
        >>> logger.info("Processing started", metadata={"files": 10})
        >>> logger.error("Failed to index", metadata={"file": "doc.pdf", "error": "timeout"})
    
    Environment variables:
        AITAO_LOG_LEVEL: Override log level (DEBUG, INFO, WARNING, ERROR)
        AITAO_QUIET: If set, disable console logging (logs still go to file)
    """
    import os
    
    # Check for environment overrides
    env_level = os.environ.get("AITAO_LOG_LEVEL", "").upper()
    if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        level = getattr(logging, env_level)
    
    quiet_mode = os.environ.get("AITAO_QUIET", "").lower() in ("1", "true", "yes")
    
    # Return cached logger if exists
    cache_key = f"{name}:{log_filename}:{level}:{quiet_mode}"
    if cache_key in _loggers:
        return _loggers[cache_key]
    
    # Create new logger
    logger = logging.getLogger(name)
    
    # Avoid adding handlers if logger already configured
    if not logger.handlers:
        logger.setLevel(level)
        logger.propagate = False  # Prevent duplicate logs
        
        # Determine log filename
        if log_filename is None:
            # Extract last part of name: 'src.core.indexer' → 'indexer.log'
            module_name = name.split('.')[-1]
            log_filename = f"{module_name}.log"
        
        # Get logs directory via PathManager
        try:
            logs_dir = path_manager.get_logs_dir()
            log_file = logs_dir / log_filename
        except Exception as e:
            # Fallback: write to system temp dir, never to CWD (issue #1)
            print(f"⚠️ Logger: PathManager unavailable ({e}), using temp fallback", file=sys.stderr)
            logs_dir = _temp_logs_dir()
            log_file = logs_dir / log_filename
        
        # File handler with JSON formatting (100MB max, 5 backups)
        file_handler = RotatingFileHandler(
            str(log_file), 
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        # Console handler with human-readable format (unless quiet mode)
        if not quiet_mode:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(HumanReadableFormatter())
            logger.addHandler(console_handler)
    
    # Wrap in StructuredLogger and cache
    structured_logger = StructuredLogger(logger)
    _loggers[cache_key] = structured_logger
    
    return structured_logger
