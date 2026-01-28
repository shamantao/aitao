#!/usr/bin/env bash

# =============================================================================
# ☯️ AI Tao V2 - Command Line Interface
# =============================================================================
# 
# Modern CLI for managing AItao V2 services
# - Document indexation and search
# - Traditional Chinese translation engine
# - Local-first, privacy-focused
#
# =============================================================================

set -euo pipefail

# --- Configuration ---
VENV_DIR=".venv"
PYTHON="$VENV_DIR/bin/python3"
AITAO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$AITAO_ROOT/config/config.yaml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Helper Functions ---

get_version() {
    $PYTHON -c "from src.core.version import get_version; print(get_version())" 2>/dev/null || echo "2.0.5"
}

print_header() {
    local version=$(get_version)
    echo -e "${BOLD}${BLUE}"
    echo "  ☯️  AI Tao V2 (v${version})"
    echo "  Document Search & Translation Engine"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Python venv
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found at $VENV_DIR"
        print_info "Run: uv venv && uv pip install -e ."
        exit 1
    fi
    
    # Check Python executable
    if [ ! -x "$PYTHON" ]; then
        print_error "Python executable not found: $PYTHON"
        exit 1
    fi
    
    # Check config file
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        
        # Check if template exists
        if [ -f "$AITAO_ROOT/config/config.yaml.template" ]; then
            print_info "Template found. Copy and customize it:"
            echo "  cp config/config.yaml.template config/config.yaml"
            echo "  vim config/config.yaml"
        fi
        
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

validate_config() {
    print_info "Validating configuration..."
    
    $PYTHON -c "
from src.core.config import ConfigManager
try:
    config = ConfigManager('$CONFIG_FILE')
    print('✅ Configuration valid')
    print(f'   Storage: {config.get(\"paths.storage_root\")}')
    print(f'   Models: {config.get(\"paths.models_dir\")}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    exit(1)
" || exit 1
}

show_config() {
    print_info "Configuration details:"
    echo ""
    
    $PYTHON -c "
from src.core.config import ConfigManager
config = ConfigManager('$CONFIG_FILE')

sections = {
    'Paths': 'paths',
    'Indexing': 'indexing',
    'OCR': 'ocr',
    'Translation': 'translation',
    'Search': 'search',
    'API': 'api',
}

for title, section in sections.items():
    print(f'\n{title}:')
    data = config.get_section(section)
    for key, value in data.items():
        if isinstance(value, dict):
            print(f'  {key}:')
            for k, v in value.items():
                print(f'    {k}: {v}')
        elif isinstance(value, list):
            if len(value) <= 3:
                print(f'  {key}: {value}')
            else:
                print(f'  {key}: [{len(value)} items]')
        else:
            print(f'  {key}: {value}')
"
}

show_status() {
    print_header
    print_info "System Status"
    echo ""
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON --version 2>&1)
    echo "Python: $PYTHON_VERSION"
    
    # Check config
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${GREEN}Config: ✓${NC} $CONFIG_FILE"
    else
        echo -e "${RED}Config: ✗${NC} $CONFIG_FILE (missing)"
    fi
    
    # Check core modules
    echo ""
    print_info "Core Modules:"
    
    $PYTHON -c "
import sys
modules_status = []

# Check core modules
try:
    from src.core.pathmanager import path_manager
    modules_status.append(('PathManager', True))
except Exception as e:
    modules_status.append(('PathManager', False))

try:
    from src.core.logger import get_logger
    modules_status.append(('Logger', True))
except Exception as e:
    modules_status.append(('Logger', False))

try:
    from src.core.config import ConfigManager
    modules_status.append(('ConfigManager', True))
except Exception as e:
    modules_status.append(('ConfigManager', False))

for module, status in modules_status:
    status_str = '✓' if status else '✗'
    color = '\033[0;32m' if status else '\033[0;31m'
    print(f'{color}{status_str}\033[0m {module}')
"
    
    # Check directories
    echo ""
    print_info "Storage Directories:"
    
    $PYTHON -c "
from src.core.config import ConfigManager
from pathlib import Path

config = ConfigManager('$CONFIG_FILE')
paths_to_check = [
    ('Storage Root', config.get('paths.storage_root')),
    ('Models', config.get('paths.models_dir')),
    ('Logs', config.get('paths.logs_dir')),
    ('Queue', config.get('paths.queue_dir')),
    ('Cache', config.get('paths.cache_dir')),
]

for name, path_str in paths_to_check:
    path = Path(path_str)
    status = '✓' if path.exists() else '✗'
    color = '\033[0;32m' if path.exists() else '\033[0;33m'
    print(f'{color}{status}\033[0m {name}: {path_str}')
"
    
    echo ""
}

run_tests() {
    print_info "Running unit tests..."
    
    cd "$AITAO_ROOT"
    
    if command -v uv &> /dev/null; then
        uv run pytest tests/unit/ -v --tb=short
    else
        $PYTHON -m pytest tests/unit/ -v --tb=short
    fi
}

show_logs() {
    local module="${1:-}"
    
    if [ -z "$module" ]; then
        print_error "Usage: $0 logs <module>"
        echo ""
        echo "Available modules:"
        
        $PYTHON -c "
from src.core.config import ConfigManager
from pathlib import Path

config = ConfigManager('$CONFIG_FILE')
logs_dir = Path(config.get('paths.logs_dir'))

if logs_dir.exists():
    log_files = sorted(logs_dir.glob('*.log'))
    for log_file in log_files:
        module_name = log_file.stem
        size = log_file.stat().st_size
        size_mb = size / (1024 * 1024)
        print(f'  - {module_name} ({size_mb:.2f} MB)')
else:
    print('  (no logs yet)')
"
        exit 1
    fi
    
    $PYTHON -c "
from src.core.config import ConfigManager
from pathlib import Path

config = ConfigManager('$CONFIG_FILE')
logs_dir = Path(config.get('paths.logs_dir'))
log_file = logs_dir / '${module}.log'

if log_file.exists():
    print(f'Showing logs: {log_file}')
    print('=' * 80)
    with open(log_file, 'r') as f:
        lines = f.readlines()
        # Show last 50 lines
        for line in lines[-50:]:
            print(line.rstrip())
else:
    print(f'❌ Log file not found: {log_file}')
    exit(1)
"
}

search_documents() {
    local query="${1:-}"
    
    if [ -z "$query" ]; then
        print_error "Usage: $0 search \"your query\""
        exit 1
    fi
    
    print_info "Searching for: \"$query\""
    print_warning "Search functionality not yet implemented (Sprint 2)"
    echo ""
    echo "This will be available after:"
    echo "  - Sprint 1: Indexation module"
    echo "  - Sprint 2: Search module (Meilisearch + LanceDB)"
}

ingest_documents() {
    local path="${1:-}"
    
    if [ -z "$path" ]; then
        print_error "Usage: $0 ingest <path>"
        exit 1
    fi
    
    if [ ! -e "$path" ]; then
        print_error "Path not found: $path"
        exit 1
    fi
    
    print_info "Ingesting: $path"
    print_warning "Ingestion functionality not yet implemented (Sprint 1)"
    echo ""
    echo "This will be available after Sprint 1 (Indexation module)"
}

start_services() {
    print_header
    print_info "Starting AItao V2 services..."
    echo ""
    
    check_prerequisites
    validate_config
    
    print_warning "Service management not yet implemented"
    echo ""
    echo "Current Sprint 0 status: Foundation modules completed"
    echo "  ✅ PathManager"
    echo "  ✅ Logger"
    echo "  ✅ ConfigManager"
    echo "  ✅ config.yaml"
    echo ""
    echo "Next sprints will implement:"
    echo "  Sprint 1: Indexation (document scanning & ingestion)"
    echo "  Sprint 2: Search (Meilisearch + LanceDB)"
    echo "  Sprint 3: OCR (PaddleOCR + Qwen-VL)"
    echo "  Sprint 4: Translation (mBART50)"
    echo "  Sprint 5: API (FastAPI REST endpoints)"
    echo "  Sprint 6: Dashboard (Web UI)"
}

stop_services() {
    print_info "Stopping AItao V2 services..."
    print_warning "No services currently running (Sprint 0)"
}

show_help() {
    print_header
    
    cat << EOF
${BOLD}Usage:${NC}
  ./aitao.sh <command> [options]

${BOLD}Commands:${NC}
  ${GREEN}status${NC}              Show system status and configuration
  ${GREEN}config${NC}              Display current configuration
  ${GREEN}config validate${NC}     Validate config.yaml syntax and values
  ${GREEN}test${NC}                Run unit tests
  ${GREEN}logs <module>${NC}       Show logs for a specific module
  
  ${YELLOW}start${NC}               Start AItao services (not yet implemented)
  ${YELLOW}stop${NC}                Stop AItao services (not yet implemented)
  ${YELLOW}ingest <path>${NC}       Index documents from path (Sprint 1)
  ${YELLOW}search "query"${NC}      Search documents (Sprint 2)
  
  ${BLUE}help${NC}                 Show this help message

${BOLD}Examples:${NC}
  ./aitao.sh status
  ./aitao.sh config validate
  ./aitao.sh test
  ./aitao.sh logs indexer

${BOLD}Configuration:${NC}
  File: config/config.yaml
  Template: config/config.yaml.template

${BOLD}Development Status:${NC}
  Sprint 0 (Foundation): ✅ Complete
    - PathManager, Logger, ConfigManager, config.yaml
  
  Sprint 1 (Indexation): 🔜 Upcoming
  Sprint 2 (Search): 🔜 Upcoming
  Sprint 3+ (OCR, Translation, API, Dashboard): 🔜 Upcoming

${BOLD}More Info:${NC}
  README.md - Full documentation
  prd/PRD.md - Product requirements
  prd/BACKLOG.md - Sprint planning

EOF
}

# --- Main Command Router ---

case "${1:-}" in
    status)
        show_status
        ;;
    
    config)
        case "${2:-}" in
            validate)
                check_prerequisites
                validate_config
                print_success "Configuration is valid"
                ;;
            *)
                check_prerequisites
                show_config
                ;;
        esac
        ;;
    
    test|tests)
        check_prerequisites
        run_tests
        ;;
    
    logs)
        check_prerequisites
        show_logs "${2:-}"
        ;;
    
    search)
        check_prerequisites
        search_documents "${2:-}"
        ;;
    
    ingest)
        check_prerequisites
        ingest_documents "${2:-}"
        ;;
    
    start)
        start_services
        ;;
    
    stop)
        stop_services
        ;;
    
    version|--version|-v)
        echo "aitao $(get_version)"
        ;;
    
    help|--help|-h|"")
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        echo ""
        echo "Run './aitao.sh help' for usage information"
        exit 1
        ;;
esac
