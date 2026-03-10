"""
Entry point for running the CLI as a module.

Usage:
    python -m cli
    python -m cli status
    python -m cli ms status
    etc.
"""

from cli.main import app


if __name__ == "__main__":
    app()
