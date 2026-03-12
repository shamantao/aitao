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


def check_critical_imports() -> list[tuple[str, bool, str, str]]:
    """Check if critical modules can be imported."""
    # (import_name, description, version_attr_or_None)
    critical_modules = [
        # Core AI / ML
        ("torch", "PyTorch (ML engine)", "__version__"),
        ("llama_cpp", "llama-cpp-python (GGUF inference)", "__version__"),
        ("transformers", "Hugging Face Transformers", "__version__"),
        ("sentence_transformers", "Sentence Transformers (embeddings)", "__version__"),
        # Databases
        ("lancedb", "Vector database (LanceDB)", "__version__"),
        ("meilisearch", "Full-text search (Meilisearch SDK)", None),
        # CLI / display
        ("typer", "CLI framework", "__version__"),
        ("rich", "Terminal formatting", None),
        # API
        ("fastapi", "REST API framework", "__version__"),
        ("uvicorn", "ASGI server", "__version__"),
        # Document extraction
        ("pypdf", "PDF extraction", "__version__"),
        ("docx", "DOCX extraction (python-docx)", "__version__"),
        ("openpyxl", "Excel extraction (.xlsx)", "__version__"),
        ("langdetect", "Language detection", "VERSION"),
        ("PIL", "Image processing (Pillow)", "__version__"),
        # Security
        ("cryptography", "License validation (RSA)", "__version__"),
        # Config & Utils
        ("toml", "TOML parsing", None),
        ("psutil", "System monitoring", "__version__"),
    ]

    results = []
    for module, description, ver_attr in critical_modules:
        try:
            m = __import__(module)
            version = getattr(m, ver_attr, "?") if ver_attr else "ok"
            results.append((module, True, description, str(version)))
        except ImportError as e:
            results.append((module, False, f"{description} - {e}", ""))

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

    for module, success, desc, version in import_results:
        if success:
            ver_str = f" ({version})" if version and version != "ok" else ""
            print(f"  {GREEN}✓{RESET} {module:<30} {ver_str}")
        else:
            print(f"  {RED}✗{RESET} {module:<30} MISSING — {desc}")
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
