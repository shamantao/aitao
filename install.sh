#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Purpose: Prepare the local environment for the AI Tao project.
#
# This script:
#   1. Detects the operating system (macOS, Linux)
#   2. Installs system dependencies (Homebrew, apt, etc.)
#   3. Installs required services (Meilisearch, Ollama)
#   4. Installs uv (Python package manager) if missing
#   5. Creates an isolated virtual environment
#   6. Installs project dependencies via pyproject.toml
#
# Usage:
#   ./install.sh              # Standard installation
#   INSTALL_DEV=1 ./install.sh  # Include dev dependencies
#   SKIP_SERVICES=1 ./install.sh  # Skip Meilisearch/Ollama install
# -----------------------------------------------------------------------------

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${VENV_PATH:-${PROJECT_ROOT}/.venv}"
INSTALL_DEV="${INSTALL_DEV:-0}"
SKIP_SERVICES="${SKIP_SERVICES:-0}"

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { printf "${GREEN}[INFO]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; }
fail() { printf "${RED}[ERROR]${NC} %s\n" "$1" >&2; exit 1; }
step() { printf "${BLUE}[STEP]${NC} %s\n" "$1"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# =============================================================================
# OS Detection
# =============================================================================
detect_os() {
    local os_name kernel_name
    kernel_name="$(uname -s)"
    
    case "$kernel_name" in
        Darwin)
            OS_TYPE="macos"
            OS_PKG_MANAGER="brew"
            log "Detected macOS ($(sw_vers -productVersion))"
            ;;
        Linux)
            OS_TYPE="linux"
            if command_exists apt-get; then
                OS_PKG_MANAGER="apt"
                log "Detected Linux (Debian/Ubuntu)"
            elif command_exists dnf; then
                OS_PKG_MANAGER="dnf"
                log "Detected Linux (Fedora/RHEL)"
            elif command_exists pacman; then
                OS_PKG_MANAGER="pacman"
                log "Detected Linux (Arch)"
            else
                OS_PKG_MANAGER="unknown"
                warn "Linux detected but no known package manager found"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            OS_TYPE="windows"
            OS_PKG_MANAGER="none"
            warn "Windows detected. Please use WSL2 for best results."
            ;;
        *)
            OS_TYPE="unknown"
            OS_PKG_MANAGER="unknown"
            warn "Unknown OS: $kernel_name"
            ;;
    esac
}

# =============================================================================
# Package Manager Installation (macOS: Homebrew)
# =============================================================================
install_homebrew() {
    if [ "$OS_TYPE" != "macos" ]; then
        return
    fi
    
    if command_exists brew; then
        log "Homebrew already installed."
        return
    fi
    
    step "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add to PATH for current session (Intel/Apple Silicon)
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    if ! command_exists brew; then
        fail "Homebrew installation failed. Please install manually."
    fi
    log "Homebrew installed successfully."
}

# =============================================================================
# Meilisearch Installation
# =============================================================================
install_meilisearch() {
    if [ "$SKIP_SERVICES" = "1" ]; then
        log "Skipping Meilisearch (SKIP_SERVICES=1)"
        return
    fi
    
    step "Checking Meilisearch..."
    
    if command_exists meilisearch; then
        log "Meilisearch already installed."
        return
    fi
    
    case "$OS_TYPE" in
        macos)
            log "Installing Meilisearch via Homebrew..."
            brew install meilisearch
            ;;
        linux)
            log "Installing Meilisearch via official script..."
            curl -L https://install.meilisearch.com | sh
            # Move to system path
            if [ -f "./meilisearch" ]; then
                sudo mv ./meilisearch /usr/local/bin/
            fi
            ;;
        *)
            warn "Cannot auto-install Meilisearch on this OS. Please install manually."
            warn "See: https://www.meilisearch.com/docs/learn/getting_started/installation"
            return
            ;;
    esac
    
    if command_exists meilisearch; then
        log "Meilisearch installed successfully."
    else
        warn "Meilisearch installation may have failed. Check manually."
    fi
}

# =============================================================================
# Ollama Installation
# =============================================================================
install_ollama() {
    if [ "$SKIP_SERVICES" = "1" ]; then
        log "Skipping Ollama (SKIP_SERVICES=1)"
        return
    fi
    
    step "Checking Ollama..."
    
    if command_exists ollama; then
        log "Ollama already installed."
        # Start service if not running
        start_ollama_service
        return
    fi
    
    case "$OS_TYPE" in
        macos)
            log "Installing Ollama via Homebrew..."
            brew install ollama
            start_ollama_service
            ;;
        linux)
            log "Installing Ollama via official script..."
            curl -fsSL https://ollama.com/install.sh | sh
            # Ollama script starts service automatically on Linux
            ;;
        *)
            warn "Cannot auto-install Ollama on this OS. Please install manually."
            warn "See: https://ollama.com/download"
            return
            ;;
    esac
    
    if command_exists ollama; then
        log "Ollama installed successfully."
    else
        warn "Ollama installation may have failed. Check manually."
    fi
}

start_ollama_service() {
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log "Ollama service is running."
        return
    fi
    
    case "$OS_TYPE" in
        macos)
            log "Starting Ollama service..."
            brew services start ollama 2>/dev/null || ollama serve &
            sleep 2
            ;;
        linux)
            log "Starting Ollama service..."
            systemctl start ollama 2>/dev/null || ollama serve &
            sleep 2
            ;;
    esac
}

# =============================================================================
# Python Check
# =============================================================================
check_python() {
    step "Checking Python..."
    
    if ! command_exists "$PYTHON_BIN"; then
        # Try to install Python
        case "$OS_TYPE" in
            macos)
                log "Installing Python via Homebrew..."
                brew install python@3.12
                PYTHON_BIN="python3.12"
                ;;
            linux)
                case "$OS_PKG_MANAGER" in
                    apt)
                        log "Installing Python via apt..."
                        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
                        ;;
                    dnf)
                        log "Installing Python via dnf..."
                        sudo dnf install -y python3 python3-pip
                        ;;
                    pacman)
                        log "Installing Python via pacman..."
                        sudo pacman -S --noconfirm python python-pip
                        ;;
                esac
                ;;
            *)
                fail "Python not found (looked for ${PYTHON_BIN}). Install Python >=3.10 first."
                ;;
        esac
    fi
    
    # Verify version
    local py_check
    py_check="$("$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if major < 3 or (major == 3 and minor < 10):
    sys.exit(1)
print(f"{major}.{minor}")
PY
)" || true

    if [ -z "$py_check" ]; then
        fail "Python version check failed. Require Python >=3.10."
    fi
    log "Python detected: ${py_check}"
}

# =============================================================================
# uv Installation
# =============================================================================
install_uv() {
    step "Checking uv..."
    
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

# =============================================================================
# Virtual Environment
# =============================================================================
create_venv() {
    step "Setting up virtual environment..."
    
    if [ -d "$VENV_PATH" ]; then
        log "Virtual environment already exists at ${VENV_PATH}."
        return
    fi
    log "Creating virtual environment in ${VENV_PATH}..."
    UV_PYTHON="$PYTHON_BIN" uv venv "$VENV_PATH"
}

# =============================================================================
# Dependencies
# =============================================================================
sync_dependencies() {
    step "Installing project dependencies..."
    
    local base_cmd=("uv" "sync")
    if [ -f "${PROJECT_ROOT}/uv.lock" ]; then
        base_cmd+=("--frozen")
    fi
    if [ "$INSTALL_DEV" != "0" ]; then
        base_cmd+=("--extra" "dev")
        log "Including dev dependencies (INSTALL_DEV=${INSTALL_DEV})."
    fi
    (cd "$PROJECT_ROOT" && UV_PYTHON="$PYTHON_BIN" "${base_cmd[@]}")
}

# =============================================================================
# Config Setup
# =============================================================================
setup_config() {
    step "Checking configuration..."
    
    local config_file="${PROJECT_ROOT}/config/config.yaml"
    local template_file="${PROJECT_ROOT}/config/config.yaml.template"
    
    if [ -f "$config_file" ]; then
        log "Configuration file exists: ${config_file}"
        return
    fi
    
    if [ -f "$template_file" ]; then
        log "Creating config.yaml from template..."
        cp "$template_file" "$config_file"
        log "Created ${config_file} - please review and customize."
    else
        warn "No config template found. Create config/config.yaml manually."
    fi
}

# =============================================================================
# Summary
# =============================================================================
print_summary() {
    echo ""
    echo "=============================================="
    echo "  AItao Installation Complete"
    echo "=============================================="
    echo ""
    echo "Environment:"
    echo "  OS:          ${OS_TYPE}"
    echo "  Python:      $(${PYTHON_BIN} --version 2>&1)"
    echo "  venv:        ${VENV_PATH}"
    echo ""
    echo "Services:"
    if command_exists meilisearch; then
        echo "  Meilisearch: ✓ installed"
    else
        echo "  Meilisearch: ✗ not found"
    fi
    if command_exists ollama; then
        echo "  Ollama:      ✓ installed"
    else
        echo "  Ollama:      ✗ not found"
    fi
    echo ""
    echo "Next steps:"
    echo "  1) Activate the virtual environment:"
    echo "     source ${VENV_PATH}/bin/activate"
    echo ""
    echo "  2) Review/edit configuration:"
    echo "     ${PROJECT_ROOT}/config/config.yaml"
    echo ""
    echo "  3) Start AItao:"
    echo "     ./aitao.sh start"
    echo ""
    echo "  4) Stop AItao:"
    echo "     ./aitao.sh stop"
    echo ""
    if [ "$INSTALL_DEV" = "0" ]; then
        echo "Tip: Re-run with INSTALL_DEV=1 for development dependencies."
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "=============================================="
    echo "  AItao Installation Script"
    echo "=============================================="
    echo ""
    log "Project root: ${PROJECT_ROOT}"
    
    # Phase 1: OS Detection
    detect_os
    
    # Phase 2: System Package Manager (macOS: Homebrew)
    if [ "$OS_TYPE" = "macos" ]; then
        install_homebrew
    fi
    
    # Phase 3: Services (Meilisearch, Ollama)
    install_meilisearch
    install_ollama
    
    # Phase 4: Python Environment
    check_python
    install_uv
    create_venv
    sync_dependencies
    
    # Phase 5: Configuration
    setup_config
    
    # Summary
    print_summary
}

main "$@"
