"""
Core infrastructure modules for AItao V2.

This package contains foundational components:
- pathmanager: Centralized path management
- logger: Structured JSON logging
- config: YAML configuration loader (TODO)
- system_monitor: System resource monitoring (TODO)
"""

from .pathmanager import AitaoPathManager, path_manager
from .logger import get_logger

__all__ = ['AitaoPathManager', 'path_manager', 'get_logger']
