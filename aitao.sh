#!/usr/bin/env bash

# =============================================================================
# ☯️ AI Tao V2 - Command Line Interface (Façade)
# =============================================================================
#
# Thin shell wrapper that delegates to the Python CLI.
# All commands are implemented in Python (src/cli/) for maintainability.
#
# Usage:
#   ./aitao.sh status          # System status
#   ./aitao.sh ms upgrade      # Meilisearch management
#   ./aitao.sh db stats        # LanceDB stats
#   ./aitao.sh config show     # Configuration
#   ./aitao.sh test            # Run unit tests
#   ./aitao.sh test -v         # Run unit tests (verbose)
#   ./aitao.sh validate        # Full validation (unit + e2e + functional)
#   ./aitao.sh contracts       # Check architecture contracts
#   ./aitao.sh contracts --stats  # Show adoption metrics only
#   ./aitao.sh benchmark       # Benchmark MLX vs Ollama backends
#   ./aitao.sh benchmark -n 5  # Benchmark with 5 iterations
#
# =============================================================================
#clear
set -euo pipefail

# --- Prevent OpenMP library conflicts (PyTorch + NumPy/scikit-learn) ---
export KMP_DUPLICATE_LIB_OK=TRUE

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
SRC_DIR="$SCRIPT_DIR/src"

# Colors for minimal output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# --- Check virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo ""
    echo "Setup with:"
    echo "  cd $SCRIPT_DIR"
    echo "  uv venv && uv pip install -e ."
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo -e "${RED}❌ Python not found in venv${NC}"
    exit 1
fi

# --- Validate (full pipeline) ---
if [ "${1:-}" = "validate" ]; then
    echo "🔍 Running full validation pipeline..."

    echo "✅ Step 1: Architecture contracts"
    "$PYTHON" "$SCRIPT_DIR/scripts/check_contracts.py" --stats
    
    echo ""
    echo "✅ Step 2: Unit tests"
    "$PYTHON" -m pytest "$SCRIPT_DIR/tests/unit" -v

    echo "✅ Step 3: E2E tests"
    "$PYTHON" -m pytest "$SCRIPT_DIR/tests/e2e" -v

    echo "✅ Step 4: Functional check (models status)"
    "$PYTHON" -m src.cli.main models status > /dev/null

    echo -e "${GREEN}✓ Validation complete${NC}"
    exit 0
fi

# --- Contracts check (architecture validation) ---
if [ "${1:-}" = "contracts" ]; then
    shift
    "$PYTHON" "$SCRIPT_DIR/scripts/check_contracts.py" "$@"
    exit $?
fi

# --- Benchmark (MLX vs Ollama) ---
if [ "${1:-}" = "benchmark" ]; then
    shift
    "$PYTHON" "$SCRIPT_DIR/scripts/benchmark_backends.py" "$@"
    exit $?
fi

# --- Delegate to Python CLI ---
# Pass original working directory for file path resolution
export AITAO_ORIG_PWD="$(pwd)"
cd "$SRC_DIR"
exec "$PYTHON" -m cli "$@"
