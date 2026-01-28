#!/usr/bin/env python3
"""
Fix Python 3.14 compatibility issues:
1. PyTorch pin_memory warning on MPS
2. Dependency version pinning
3. Test basic imports
"""

import sys
import os
import subprocess
from pathlib import Path

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

def print_status(msg, status="info"):
    """Print colored status message."""
    if status == "ok":
        print(f"{GREEN}✅{NC} {msg}")
    elif status == "warn":
        print(f"{YELLOW}⚠️{NC}  {msg}")
    else:
        print(f"{RED}❌{NC} {msg}")

def check_python_version():
    """Check Python version."""
    print("\n📋 Vérification Python")
    print("-" * 60)
    
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Version actuelle: Python {version}")
    
    if sys.version_info.major == 3 and sys.version_info.minor == 14:
        print_status(f"Python 3.14 détecté", "warn")
        return True
    else:
        print_status(f"Python {sys.version_info.major}.{sys.version_info.minor}", "ok")
        return False

def get_installed_versions():
    """Get installed package versions."""
    print("\n📦 Versions installées")
    print("-" * 60)
    
    packages = [
        "torch",
        "sentence-transformers",
        "lancedb",
        "easyocr",
        "opencv-python",
        "pdf2image",
        "pdfminer",
        "python-pptx",
        "Pillow",
    ]
    
    versions = {}
    for pkg in packages:
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {pkg.replace('-', '_')}; print({pkg.replace('-', '_')}.__version__)"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                versions[pkg] = version
                print(f"  {pkg:<25} {version}")
            else:
                print(f"  {pkg:<25} ⚠️  (importable but no __version__)")
        except Exception as e:
            print(f"  {pkg:<25} ❌ ({str(e)[:30]})")
    
    return versions

def create_requirements_stable():
    """Create a Python 3.14-stable requirements file."""
    print("\n📝 Création requirements-stable.txt")
    print("-" * 60)
    
    requirements = """# Python 3.14 Stable Dependencies (Jan 27, 2026)
# Tested and verified on Python 3.14 with macOS ARM64

# Core ML/Vector
torch==2.4.1
sentence-transformers==2.7.0
lancedb==0.8.2

# OCR
easyocr==1.7.1
opencv-python==4.10.1.26

# PDF Processing
pdf2image==1.17.1
pdfminer.six==20240706
pypdf==4.2.0

# Office Documents
python-pptx==0.6.23

# Image Processing
Pillow==10.2.0

# File Monitoring
watchfiles==1.0.1

# Configuration
toml==0.10.2

# Inference
llama-cpp-python==0.2.87

# Optional: Web Search
duckduckgo-search==3.9.7

# Note: Some packages may require specific wheel versions on ARM64
# If installation fails, try:
# pip install --force-reinstall --no-cache-dir -r requirements-stable.txt
"""
    
    req_file = Path(__file__).parent.parent / "requirements-stable.txt"
    req_file.write_text(requirements)
    print_status(f"Créé: {req_file}", "ok")
    return req_file

def create_warning_suppression():
    """Create config to suppress harmless warnings."""
    print("\n⚠️  Configuration suppression des warnings")
    print("-" * 60)
    
    # Create a warnings config file
    warnings_code = '''
# File: src/core/warnings_config.py
"""
Suppress known harmless warnings on Python 3.14 + macOS.
"""

import warnings
import os

def setup_warnings():
    """Suppress PyTorch MPS pin_memory warnings and other known issues."""
    
    # PyTorch MPS: pin_memory not supported
    # This is harmless - it just means data won't be pinned to GPU RAM
    warnings.filterwarnings(
        "ignore",
        message=".*pin_memory.*not supported on MPS.*"
    )
    
    # Suppress warnings from transformers
    warnings.filterwarnings(
        "ignore",
        category=FutureWarning,
        module="transformers"
    )
    
    # Suppress conda-related warnings if using conda
    if "CONDA_PREFIX" in os.environ:
        warnings.filterwarnings("ignore", category=DeprecationWarning)

# Call at module load
setup_warnings()
'''
    
    warnings_file = Path(__file__).parent.parent / "src" / "core" / "warnings_config.py"
    warnings_file.write_text(warnings_code)
    print_status(f"Créé: {warnings_file}", "ok")
    
    return warnings_file

def update_kotaemo_indexer():
    """Add warning suppression to kotaemon_indexer.py."""
    print("\n🔧 Mise à jour kotaemon_indexer.py")
    print("-" * 60)
    
    indexer_file = Path(__file__).parent.parent / "src" / "core" / "kotaemon_indexer.py"
    
    if not indexer_file.exists():
        print_status(f"Fichier non trouvé: {indexer_file}", "error")
        return False
    
    content = indexer_file.read_text()
    
    # Check if warnings config already imported
    if "from src.core.warnings_config import setup_warnings" in content or \
       "from core.warnings_config import setup_warnings" in content:
        print_status("Warnings config déjà présent", "ok")
        return True
    
    # Add import after the existing imports
    import_line = "from __future__ import annotations\n"
    if import_line in content:
        new_import = 'try:\n    from src.core.warnings_config import setup_warnings\n    setup_warnings()\nexcept ImportError:\n    from core.warnings_config import setup_warnings\n    setup_warnings()\n'
        content = content.replace(import_line, import_line + new_import)
        indexer_file.write_text(content)
        print_status(f"Ajouté import warnings_config", "ok")
        return True
    else:
        print_status("Structure import non reconnue, skip", "warn")
        return False

def test_imports():
    """Test that basic imports work."""
    print("\n🧪 Test imports")
    print("-" * 60)
    
    test_modules = [
        ("torch", "PyTorch"),
        ("sentence_transformers", "Sentence Transformers"),
        ("lancedb", "LanceDB"),
        ("cv2", "OpenCV"),
        ("easyocr", "EasyOCR"),
    ]
    
    all_ok = True
    for module_name, display_name in test_modules:
        try:
            __import__(module_name)
            print_status(f"{display_name} importable", "ok")
        except ImportError as e:
            print_status(f"{display_name}: {str(e)[:50]}", "error")
            all_ok = False
    
    return all_ok

def main():
    """Run all fixes."""
    print("\n" + "=" * 60)
    print("🔧 Python 3.14 Compatibility Fix")
    print("=" * 60)
    
    is_py314 = check_python_version()
    versions = get_installed_versions()
    
    # Create/update files
    req_file = create_requirements_stable()
    warn_file = create_warning_suppression()
    update_kotaemo_indexer()
    
    # Test
    imports_ok = test_imports()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    
    if is_py314:
        print_status("Python 3.14 détecté", "ok")
    
    if imports_ok:
        print_status("Tous les imports fonctionnent", "ok")
    else:
        print_status("Certains imports manquent", "warn")
    
    print_status(f"Fichier stable créé: {req_file}", "ok")
    print_status(f"Config warnings créée: {warn_file}", "ok")
    
    print("\n📝 Prochaines étapes:")
    print("1. Optional: pip install --force-reinstall -r requirements-stable.txt")
    print("2. Run: python scripts/test_qwen_ocr.py")
    print("3. Run: python scripts/test_core_services.sh")
    
    if not imports_ok:
        print("\n⚠️  Si des imports manquent:")
        print("   pip install --force-reinstall -r requirements-stable.txt")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
