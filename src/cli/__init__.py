"""
AItao CLI - Command Line Interface.

This module provides a modular CLI for AItao operations:
- Typer-based command routing
- Rich console output with colors and progress bars
- Modular command structure in commands/ subdirectory

Usage:
    python -m aitao.cli <command> [options]
    
Or via the shell wrapper:
    ./aitao.sh <command> [options]
"""

__all__ = ["app"]
