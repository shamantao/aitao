"""
Unit tests for the structured Logger module.

Tests cover:
- Logger initialization and configuration
- JSON formatting
- Metadata support
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log rotation
- Multiple loggers with separate files
"""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from src.core.logger import (
    get_logger,
    JSONFormatter,
    HumanReadableFormatter,
    StructuredLogger,
)


class TestJSONFormatter:
    """Test JSON log formatter."""
    
    def test_json_formatter_basic(self):
        """Test JSONFormatter outputs valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)  # Should not raise
        
        assert data["level"] == "INFO"
        assert data["module"] == "test_module"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")
    
    def test_json_formatter_with_metadata(self):
        """Test JSONFormatter includes metadata."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="indexer",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="File indexed",
            args=(),
            exc_info=None
        )
        record.metadata = {"file": "test.pdf", "pages": 5}
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "metadata" in data
        assert data["metadata"]["file"] == "test.pdf"
        assert data["metadata"]["pages"] == 5
    
    def test_json_formatter_with_exception(self):
        """Test JSONFormatter captures exceptions."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test error" in data["exception"]


class TestHumanReadableFormatter:
    """Test human-readable console formatter."""
    
    def test_human_readable_format(self):
        """Test HumanReadableFormatter outputs readable text."""
        formatter = HumanReadableFormatter()
        record = logging.LogRecord(
            name="test_module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        
        assert "[INFO]" in output
        assert "[test_module]" in output
        assert "Test message" in output


class TestStructuredLogger:
    """Test StructuredLogger wrapper."""
    
    def test_structured_logger_levels(self):
        """Test all log levels work correctly."""
        base_logger = logging.getLogger("test_levels")
        base_logger.handlers = []  # Clear handlers
        base_logger.setLevel(logging.DEBUG)
        
        # Mock handler to capture logs
        mock_handler = MagicMock()
        mock_handler.level = logging.DEBUG  # Set level for comparison
        base_logger.addHandler(mock_handler)
        
        logger = StructuredLogger(base_logger)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        assert mock_handler.handle.call_count == 5
    
    def test_structured_logger_metadata(self):
        """Test metadata is passed correctly."""
        base_logger = logging.getLogger("test_metadata")
        base_logger.handlers = []
        base_logger.setLevel(logging.INFO)
        
        mock_handler = MagicMock()
        mock_handler.level = logging.INFO  # Set level for comparison
        base_logger.addHandler(mock_handler)
        
        logger = StructuredLogger(base_logger)
        metadata = {"key": "value", "count": 42}
        
        logger.info("Test with metadata", metadata=metadata)
        
        call_args = mock_handler.handle.call_args
        record = call_args[0][0]
        assert hasattr(record, 'metadata')
        assert record.metadata == metadata


class TestGetLogger:
    """Test get_logger function and integration."""
    
    @pytest.fixture
    def temp_logs_dir(self):
        """Create a temporary logs directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_logger_returns_structured_logger(self, temp_logs_dir, monkeypatch):
        """Test get_logger returns StructuredLogger instance."""
        # Mock PathManager
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger = get_logger("test_module")
            
            assert isinstance(logger, StructuredLogger)
    
    def test_get_logger_creates_log_file(self, temp_logs_dir, monkeypatch):
        """Test get_logger creates log file."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger = get_logger("test_create")
            logger.info("Test message")
            
            log_file = temp_logs_dir / "test_create.log"
            assert log_file.exists()
    
    def test_get_logger_custom_filename(self, temp_logs_dir, monkeypatch):
        """Test get_logger with custom filename."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger = get_logger("module", log_filename="custom.log")
            logger.info("Test")
            
            log_file = temp_logs_dir / "custom.log"
            assert log_file.exists()
    
    def test_get_logger_json_output(self, temp_logs_dir, monkeypatch):
        """Test logger outputs valid JSON to file."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger = get_logger("test_json")
            logger.info("Test message", metadata={"key": "value"})
            
            log_file = temp_logs_dir / "test_json.log"
            content = log_file.read_text()
            
            # Parse JSON (should not raise)
            log_entry = json.loads(content.strip())
            
            assert log_entry["level"] == "INFO"
            assert log_entry["message"] == "Test message"
            assert log_entry["metadata"]["key"] == "value"
    
    def test_get_logger_caching(self, temp_logs_dir, monkeypatch):
        """Test get_logger returns cached instance."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger1 = get_logger("cached_module")
            logger2 = get_logger("cached_module")
            
            assert logger1 is logger2
    
    def test_get_logger_separate_files(self, temp_logs_dir, monkeypatch):
        """Test multiple loggers create separate log files."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger1 = get_logger("module1")
            logger2 = get_logger("module2")
            
            logger1.info("Message 1")
            logger2.info("Message 2")
            
            file1 = temp_logs_dir / "module1.log"
            file2 = temp_logs_dir / "module2.log"
            
            assert file1.exists()
            assert file2.exists()
            assert "Message 1" in file1.read_text()
            assert "Message 2" in file2.read_text()
    
    def test_get_logger_custom_level(self, temp_logs_dir, monkeypatch):
        """Test get_logger respects custom log level."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.return_value = temp_logs_dir
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            logger = get_logger("test_level", level=logging.WARNING)
            
            logger.debug("Debug message")  # Should not appear
            logger.info("Info message")    # Should not appear
            logger.warning("Warning message")  # Should appear
            
            log_file = temp_logs_dir / "test_level.log"
            content = log_file.read_text()
            
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
    
    def test_get_logger_fallback_on_error(self, temp_logs_dir, monkeypatch):
        """Test get_logger falls back gracefully if PathManager fails."""
        mock_path_manager = MagicMock()
        mock_path_manager.get_logs_dir.side_effect = Exception("PathManager error")
        
        with patch('src.core.logger.path_manager', mock_path_manager):
            # Should not raise, should use fallback ./logs/
            logger = get_logger("fallback_test")
            logger.info("Test message")
            
            # Logger should still work (fallback to ./logs/)
            assert isinstance(logger, StructuredLogger)
