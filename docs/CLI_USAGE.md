# AItao CLI Usage Guide

## Quick Reference

### System Status & Management
```bash
./aitao.sh status      # Show overall system health
./aitao.sh version     # Show version information
```

### Start/Stop/Restart ALL Services ⭐ (User-Friendly)
```bash
./aitao.sh start       # Start all services (Meilisearch, Worker)
./aitao.sh stop        # Stop all services
./aitao.sh restart     # Restart all services

# These are shortcuts for:
./aitao.sh lifecycle start
./aitao.sh lifecycle stop
./aitao.sh lifecycle restart
```

### Meilisearch (Full-text Search)
```bash
./aitao.sh ms status    # Check if server is running
./aitao.sh ms start     # Start server
./aitao.sh ms stop      # Stop server
./aitao.sh ms restart   # Restart server
./aitao.sh ms upgrade   # Upgrade to latest version
./aitao.sh ms rebuild   # Clear and rebuild index
```

### LanceDB (Vector Database)
```bash
./aitao.sh db status           # Show database status
./aitao.sh db stats            # Detailed statistics
./aitao.sh db clear            # Clear all embeddings
./aitao.sh db search "query"   # Test semantic search
```

### Configuration Management
```bash
./aitao.sh config show          # Display current config
./aitao.sh config show paths    # Show specific section
./aitao.sh config validate      # Validate configuration
./aitao.sh config edit          # Open in editor
```

### Document Scanning
```bash
./aitao.sh scan run             # Scan for new/modified files
./aitao.sh scan run --dry-run   # Preview without saving
./aitao.sh scan paths           # Show configured scan paths
./aitao.sh scan status          # Show scanner state
./aitao.sh scan clear           # Reset state (force full rescan)
```

### Task Queue
```bash
./aitao.sh queue status              # Show queue statistics
./aitao.sh queue list                # List tasks in queue
./aitao.sh queue list --pending      # Show only pending tasks
./aitao.sh queue add <file>          # Add file to queue
./aitao.sh queue retry               # Retry failed tasks
./aitao.sh queue clear               # Clear completed tasks
```

### Background Worker
```bash
./aitao.sh worker status             # Show worker status
./aitao.sh worker start              # Start worker daemon
./aitao.sh worker start -f           # Run in foreground (debug)
./aitao.sh worker stop               # Stop worker daemon
./aitao.sh worker restart            # Restart worker
./aitao.sh worker logs               # Show worker logs
```

### Interactive Chat
```bash
# Interactive CLI chat with RAG
python -m src.cli.chat

# With specific model
python -m src.cli.chat --model llama3.1:8b

# Without context display
python -m src.cli.chat --no-context

# Chat commands:
#   /quit, /exit, /q     - Exit chat
#   /clear                - Clear conversation
#   /context on|off       - Toggle context display
#   /stats                - Show session statistics
#   /model <name>         - Switch model
#   /history              - Show conversation history
#   /help                 - Show help
```

### Testing
```bash
./aitao.sh test                 # Run all unit tests
```

## Workflows

### Quick Start Services (NEW! 🌟)
```bash
# Start everything at once
./aitao.sh start

# Check status
./aitao.sh status

# Stop everything when done
./aitao.sh stop
```

### Start Fresh Services
```bash
# Simple way (NEW!) - Start all services at once
./aitao.sh start

# Or if you prefer to manage individually:

# Stop Meilisearch only
./aitao.sh ms stop

# Start Meilisearch only
./aitao.sh ms start

# Check status
./aitao.sh status
```

### Full Workflow: Scan, Index, Search
```bash
# 1. Check system
./aitao.sh status

# 2. Scan for documents
./aitao.sh scan run

# 3. Check queue
./aitao.sh queue status

# 4. Start/ensure worker running
./aitao.sh worker status

# 5. Search documents
./aitao.sh search "your query"
```

### Debugging
```bash
# Enable debug output
./aitao.sh -d status

# Run worker in foreground (see all logs)
./aitao.sh worker start -f

# Check specific database
./aitao.sh db stats

# View configuration with debug info
./aitao.sh config show
```

## Tips

### ✅ DO:
- Use `./aitao.sh start` and `./aitao.sh stop` for all services (easiest!)
- Use `ms stop` and `ms start` for Meilisearch only
- Use `worker stop` for background daemon
- Check `status` first to diagnose issues
- Use `-f` (foreground) flag for debugging

### ❌ DON'T:
- Don't use `./aitao.sh stop` alone anymore (use `./aitao.sh stop` for all! ✨)
- Don't assume services are running without checking `status`

## Environment Variables

### Configuration Variables
```bash
# Uses variables from config.yaml:
${HOME}          - User home directory
${storage_root}  - Main data directory
${models_dir}    - GGUF models directory

# Example from config:
storage_root: "${HOME}/Downloads/_sources/aitao"
models_dir: "${HOME}/Downloads/_sources/AI-models"
```

### Override Configuration
```bash
# Set specific paths
export AITAO_STORAGE_ROOT="/path/to/data"
export AITAO_MODELS_DIR="/path/to/models"

# Then run
./aitao.sh status
```

## Help Command

Get detailed help for any command:
```bash
./aitao.sh --help              # Root help
./aitao.sh ms --help           # Meilisearch help
./aitao.sh db --help           # LanceDB help
./aitao.sh worker --help       # Worker help
./aitao.sh status --help       # Status help
```

---

**Version:** v2.3.20  
**Last Updated:** 2026-01-29  
**Branch:** pdr/v2-remodular
