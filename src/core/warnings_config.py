
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
