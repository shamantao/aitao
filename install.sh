#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Purpose: Prepare the local environment for the AI Tao project.
# - Check required tools (Python, curl, uv)
# - Install uv if missing
# - Create an isolated virtual environment for this project
# - Install project dependencies with uv using pyproject.toml (and uv.lock if present)
# -----------------------------------------------------------------------------

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${VENV_PATH:-${PROJECT_ROOT}/.venv}"
INSTALL_DEV="${INSTALL_DEV:-0}"

log() { printf "[INFO] %s\n" "$1"; }
warn() { printf "[WARN] %s\n" "$1"; }
fail() { printf "[ERROR] %s\n" "$1" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

check_python() {
    if ! command_exists "$PYTHON_BIN"; then
        fail "Python not found (looked for ${PYTHON_BIN}). Install Python >=3.10 first."
    fi

    local py_check
    py_check="$("$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if major < 3 or (major == 3 and minor < 10):
    sys.exit(1)
print(f"{major}.{minor}")
PY
)"

    if [ -z "$py_check" ]; then
        fail "Python version check failed. Require Python >=3.10."
    fi
    log "Python detected: ${py_check}"
}

install_uv() {
    if command_exists uv; then
        log "uv already installed."
        return
    fi

    if ! command_exists curl; then
        fail "curl is required to install uv automatically. Install curl and re-run."
    fi

    log "Installing uv (official installer)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command_exists uv; then
        fail "uv installation finished but uv not found in PATH. Add $HOME/.local/bin to PATH and retry."
    fi
    log "uv installed."
}

create_venv() {
    if [ -d "$VENV_PATH" ]; then
        log "Virtual environment already exists at ${VENV_PATH}."
        return
    fi
    log "Creating virtual environment in ${VENV_PATH}..."
    UV_PYTHON="$PYTHON_BIN" uv venv "$VENV_PATH"
}

sync_dependencies() {
    local base_cmd=("uv" "sync")
    if [ -f "${PROJECT_ROOT}/uv.lock" ]; then
        base_cmd+=("--frozen")
    fi
    if [ "$INSTALL_DEV" != "0" ]; then
        base_cmd+=("--extra" "dev")
        log "Including dev dependencies (INSTALL_DEV=${INSTALL_DEV})."
    fi
    log "Installing project dependencies..."
    (cd "$PROJECT_ROOT" && UV_PYTHON="$PYTHON_BIN" "${base_cmd[@]}")
}

print_next_steps() {
    cat <<EOF

Done. Next steps:
1) Activate the virtual environment:
   source ${VENV_PATH}/bin/activate

2) Start AI Tao with the simple wrapper:
    ./aitao.sh start

    Stop everything:
    ./aitao.sh stop

3) To include dev dependencies next time, re-run with INSTALL_DEV=1:
   INSTALL_DEV=1 ./install.sh
EOF
}

main() {
    log "Project root: ${PROJECT_ROOT}"
    check_python
    install_uv
    create_venv
    sync_dependencies
    print_next_steps
}

main "$@"
