#!/usr/bin/env bash

# =============================================================================
# ☯️ AI Tao V2 - Command Line Interface (Façade)
# =============================================================================
#
# Thin shell wrapper that delegates to the Python CLI.
# All commands are implemented in Python (src/cli/) for maintainability.
#
# Usage:
#   ./aitao.sh status
#   ./aitao.sh ms upgrade
#   ./aitao.sh db stats
#   ./aitao.sh config show
#
# =============================================================================
clear
set -euo pipefail

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

# --- Delegate to Python CLI ---
# Pass original working directory for file path resolution
export AITAO_ORIG_PWD="$(pwd)"
cd "$SRC_DIR"
exec "$PYTHON" -m cli "$@"
