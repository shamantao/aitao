"""
aitao_cli.py — OS-agnostic entry point for the AiTao CLI.

Registered as [project.scripts] in pyproject.toml, which generates:
  - macOS/Linux : .venv/bin/aitao
  - Windows     : .venv\\Scripts\\aitao.exe

This wrapper ensures src/ is in sys.path before importing the Typer app,
mirroring what aitao.sh does via 'cd src/'.
"""

import sys
import os

# Add src/ to sys.path so 'from cli...' and 'from core...' imports work
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from cli.main import app  # noqa: E402


def main():
    app()


if __name__ == "__main__":
    main()
