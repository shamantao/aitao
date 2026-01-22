#!/usr/bin/env python3
"""
Helper script to export PathManager configuration to Bash.
Usage: eval $(python scripts/get_config_env.py)
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.core.aitao_configpath import path_manager
    
    logs_dir = path_manager.get_logs_dir()
    storage_root = path_manager.get_storage_root()
    models_dir = path_manager.get_models_dir()
    
    # Print as bash exports
    print(f"export AITAO_LOGS_DIR='{logs_dir}'")
    print(f"export AITAO_STORAGE_ROOT='{storage_root}'")
    print(f"export AITAO_MODELS_DIR='{models_dir}'")

except ImportError:
    # Fallback defaults if imports fail (minimal bootstrap)
    print("export AITAO_LOGS_DIR='./logs'")
except Exception as e:
    # Print generic error safely to not break eval
    print(f"# Error loading config: {e}")
