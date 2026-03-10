#!/usr/bin/env python3
"""
Worker daemon launcher script.

This script is called by BackgroundWorker.start_daemon() to start the worker
in a separate subprocess. This avoids os.fork() which is incompatible with
Metal/MPS GPU libraries on macOS.

Usage:
    python scripts/run_worker.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.indexation.worker import BackgroundWorker


def main():
    """Start the background worker."""
    # Worker will find config automatically via project root detection
    worker = BackgroundWorker()
    worker._write_pid_file()
    worker.run()


if __name__ == "__main__":
    main()
