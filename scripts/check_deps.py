#!/usr/bin/env python3
"""
Dependency verification script for AItao.

This script ensures all critical dependencies can be imported.
Use this to verify your environment is correctly set up.

Run: python scripts/check_deps.py
"""

import sys
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_critical_imports() -> list[tuple[str, bool, str]]:
    """Check if critical modules can be imported."""
    critical_modules = [
        # Core AI
        ("sentence_transformers", "Embeddings (sentence-transformers)"),
        # Databases
        ("lancedb", "Vector database (LanceDB)"),
        ("meilisearch", "Full-text search (Meilisearch SDK)"),
        # CLI
        ("typer", "CLI framework"),
        ("rich", "Terminal formatting"),
        # API
        ("fastapi", "REST API framework"),
        ("uvicorn", "ASGI server"),
        # Document extraction
        ("pypdf", "PDF extraction"),
        ("docx", "DOCX extraction (python-docx)"),
        ("langdetect", "Language detection"),
        # Config & Utils
        ("toml", "TOML parsing"),
        ("psutil", "System monitoring"),
    ]
    
    results = []
    for module, description in critical_modules:
        try:
            __import__(module)
            results.append((module, True, description))
        except ImportError as e:
            results.append((module, False, f"{description} - {e}"))
    
    return results


def check_pyproject_exists() -> bool:
    """Check if pyproject.toml exists."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    return pyproject_path.exists()


def main():
    """Run dependency checks."""
    print(f"\n{BOLD}🔍 AItao Dependency Check{RESET}")
    print("=" * 50)
    
    # Check pyproject.toml
    print(f"\n{BOLD}1. Project Configuration:{RESET}")
    if check_pyproject_exists():
        print(f"  {GREEN}✓{RESET} pyproject.toml found")
    else:
        print(f"  {RED}✗{RESET} pyproject.toml NOT FOUND")
        return 1
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  {GREEN}✓{RESET} Python {py_version}")
    
    # Check uv availability
    import shutil
    if shutil.which("uv"):
        print(f"  {GREEN}✓{RESET} uv package manager available")
    else:
        print(f"  {YELLOW}⚠{RESET} uv not found (recommended for dependency management)")
    
    # Check critical imports
    print(f"\n{BOLD}2. Critical Module Imports:{RESET}")
    import_results = check_critical_imports()
    failed_imports = []
    
    for module, success, desc in import_results:
        if success:
            print(f"  {GREEN}✓{RESET} {module}")
        else:
            print(f"  {RED}✗{RESET} {module} - MISSING")
            failed_imports.append(module)
    
    # Summary
    print(f"\n{BOLD}Summary:{RESET}")
    print("=" * 50)
    
    if not failed_imports:
        print(f"{GREEN}✓ All {len(import_results)} dependencies OK!{RESET}")
        print(f"\n{BOLD}Environment ready for AItao development.{RESET}")
        return 0
    else:
        print(f"{RED}✗ {len(failed_imports)} missing dependencies{RESET}")
        print(f"\n{BOLD}To fix, run:{RESET}")
        print(f"  {YELLOW}uv pip install -e .[dev]{RESET}")
        print(f"\nOr install individually:")
        
        # Map module names to pip package names
        module_to_package = {
            "sentence_transformers": "sentence-transformers",
            "docx": "python-docx",
        }
        
        for mod in failed_imports:
            pkg = module_to_package.get(mod, mod)
            print(f"  {YELLOW}uv pip install {pkg}{RESET}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
