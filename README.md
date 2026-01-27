# ☯️ AI Tao

Local-first, private, and modular AI assistant. Everything runs on your machine; no cloud dependencies.

**Key Principle:** *"Your data are your own. What happens on your machine, stays on your machine."*

---

## What Works Today

- ✅ **Configuration-driven:** Single `config.toml` source of truth
- ✅ **CLI orchestrator:** `aitao.sh` manages all services (start/stop/status/check)
- ✅ **RAG pipeline:** Full semantic search with vector similarity + OCR
- ✅ **Inference API:** `llama-cpp-python` on port 8247 (OpenAI-compatible)
- ✅ **RAG Server API:** Model-agnostic search on port 8200
- ✅ **AnythingLLM UI:** Chat interface on port 3001 (optional)
- ✅ **File watching:** Real-time indexing via Sync Agent
- ✅ **OCR routing:** EasyOCR (fast) + Qwen2.5-VL (advanced) with smart selection
- ✅ **Error recovery:** SHA256-based tracking + retry logic
- ✅ **Admin dashboard:** Gradio monitoring & manual re-indexing

---

## Quick Setup

### Prerequisites
- Python 3.10+ (tested on 3.14.2)
- Docker (for AnythingLLM UI) or use API-only mode
- ~10GB disk space minimum

### 1. Installation & Configuration

```bash
# Clone repository
git clone <repo-url>
cd aitao

# Install dependencies
uv sync  # or: pip install -r requirements.txt

# Initialize configuration
cp config/config.toml.template config/config.toml

# Edit configuration (customize paths, ports, models)
nano config/config.toml
```

### 2. System Check

Before first launch, verify your system:

```bash
# Complete compatibility check
./aitao.sh check system

# Validate configuration syntax
./aitao.sh check config

# Preview indexing paths
./aitao.sh check scan
```

### 3. Launch Services

```bash
# Start all services: API (8247) + UI (3001) + Sync Agent + RAG Server (8200)
./aitao.sh start

# Check service health
./aitao.sh status

# Access interfaces
#   • Web UI: http://localhost:3001
#   • API Docs: http://localhost:8247/docs
#   • RAG API: http://localhost:8200/health
```

### 4. Verify It's Working

```bash
# Test RAG search
curl http://localhost:8200/v1/rag/search?query=your+search+term&limit=5

# Check indexed documents
curl http://localhost:8200/v1/rag/stats/_default
```

---

## Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────┐
│           Configuration (config.toml)       │ ← Single Source of Truth
└─────────────────────────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │   aitao.sh (Orchestrator)│ ← Manages all services
        └─────────────────────────┘
         ↙      ↓       ↘      ↖
    ┌──────┐ ┌──────┐ ┌─────┐ ┌────────┐
    │ API  │ │  UI  │ │ RAG │ │ Sync   │
    │ 8247 │ │ 3001 │ │ 8200│ │ Agent  │
    └──────┘ └──────┘ └─────┘ └────────┘
       ↓        ↓        ↓         ↓
    ┌─────────────────────────────────────┐
    │     LanceDB (Vector Storage)         │
    │  + Indexing Pipeline (OCR/Text)     │
    │  + Failed Files Tracking             │
    └─────────────────────────────────────┘
```

### Services & Ports

| Port | Service | Role | Status |
|------|---------|------|--------|
| **8247** | API Server | Inference (OpenAI-compatible) | ✅ Active |
| **3001** | AnythingLLM UI | Chat interface, workspace management | ✅ Active |
| **8200** | RAG Server | Document search (model-agnostic) | ✅ Active |
| N/A | Sync Agent | File watching, auto-indexing | ✅ Active |

### Key Architecture Principles

1. **Configuration-Driven:** All settings in `config.toml`, no hardcoded paths
2. **Modular:** Each component can be used independently
3. **Model-Agnostic:** Apps choose their model (Qwen, Llama, etc.) while accessing shared RAG
4. **Graceful Degradation:** Services work even if optional dependencies (lancedb) are missing
5. **Privacy-First:** Everything runs locally, no external API calls (except optional web search)

---

## Quick Start

---

## Usage Examples

### Search Documents via RAG API

```bash
# Simple search
curl -X POST http://localhost:8200/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "budget forecast", "limit": 5}'

# Get document statistics
curl http://localhost:8200/v1/rag/stats/_default

# List available workspaces
curl http://localhost:8200/v1/rag/workspaces
```

### Query via Inference API (OpenAI-compatible)

```bash
# Chat completion
curl -X POST http://localhost:8247/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "aitao-model",
    "messages": [{"role": "user", "content": "What is RAG?"}]
  }'
```

### Monitor Failed Files

```bash
# View statistics
python scripts/manage_failed_files.py stats

# List all failed files
python scripts/manage_failed_files.py list

# Retry failed indexing (max 3 retries)
python scripts/manage_failed_files.py retry --max-retries 3

# Export failed files to JSON
python scripts/manage_failed_files.py export failed_files.json
```

### Admin Dashboard

```bash
# Start Gradio admin dashboard
python src/core/admin_dashboard.py
# Opens: http://localhost:7860
```

## Configuration Reference

### `config.toml` Structure

```toml
[system]
storage_root = "/path/to/storage"    # Where vectors, logs, failed files live
logs_path = "$storage_root/logs"     # Supports variable substitution

[server]
api_host = "0.0.0.0"                 # API listen address
api_port = 8247                      # Inference API (llama-cpp-python)
ui_port = 3001                       # AnythingLLM UI
rag_port = 8200                      # RAG Server API

[models]
models_dir = "/path/to/gguf/models"  # GGUF model files

[indexing]
include_paths = [                    # Folders to index
  "/Users/you/Documents",
  "/Users/you/Projects"
]
exclude_dirs = ["__pycache__", ".git", "node_modules"]
exclude_files = [".DS_Store"]
exclude_extensions = [".lock", ".log"]

[ocr]
engine = "auto"                      # "auto", "easyocr", or "qwen"
table_area_min = 0.15                # Min area % for table detection
min_intersections = 4                # Grid lines needed for table
min_line_density = 0.0005            # Line coverage threshold
```

### Storage Locations

```
$storage_root/
├── lancedb/                         # Vector database
│   └── default.lance                # Default collection
├── logs/                            # Application logs
│   ├── api.log
│   ├── sync.log
│   ├── rag_server.log
│   └── kotaemo_indexer.log
├── history/                         # Chat history (if used)
├── anythingllm-storage/             # AnythingLLM Docker mount
└── failed_files.json                # Tracks files that failed to index
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check for port conflicts
lsof -i :8247 :3001 :8200

# Kill conflicting process (replace PID)
kill -9 <PID>

# Or change ports in config.toml
```

### Docker Not Starting

```bash
# macOS: Launch Docker manually
open -a Docker

# Linux: Start Docker daemon
sudo systemctl start docker

# Wait 10 seconds, then retry
./aitao.sh start
```

### Indexing Slow or Failing

```bash
# Check logs
tail -f /path/to/storage_root/logs/kotaemo_indexer.log

# View failed files
python scripts/manage_failed_files.py list

# Retry with verbose logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.core.kotaemo_indexer import AITaoIndexer
indexer = AITaoIndexer()
indexer.index_files(['/path/to/file.pdf'])
"
```

### Missing Optional Dependencies

AI Tao gracefully degrades:
- Without **lancedb**: Vector indexing disabled, RAG returns empty results
- Without **sentence-transformers**: Embedding generation disabled  
- Without **easyocr**: Image OCR unavailable (Qwen-VL still works)

To install:
```bash
uv sync          # Full installation via uv
# OR
pip install lancedb sentence-transformers easyocr
```

---

## Development & Testing

### Run Test Suite

```bash
# Quick validation (5 seconds)
bash QUICK_TEST.sh

# Critical bug fixes validation
bash scripts/test_critical_bugs.sh

# Module import tests
python scripts/test_imports.py
```

### Manual Testing

```bash
# Terminal 1: Start inference API
python -m src.core.server --port 8247

# Terminal 2: Start RAG server
python -m src.core.rag_server

# Terminal 3: Start sync agent (watches folders)
python -m src.core.sync_agent

# Terminal 4: Test RAG API
curl http://localhost:8200/health
```

---

## Project Status & Roadmap

**Current Phase:** Phase 1 - Foundation (75% complete as of Jan 27, 2026)

**Validation Results (Latest):**
- ✅ Configuration management (TOML parsing)
- ✅ CLI orchestration (all commands working)
- ✅ RAG pipeline (bug fixed & tested)
- ✅ Sync agent (critical bug fixed)
- ✅ Failed file tracking (functioning)
- ✅ System verification (14/14 checks passed)
- 📋 E2E testing (Phase 2 task)

**Next Phase:** Phase 2 - Core Features (Ready to start)
- 🔮 Web search integration (DuckDuckGo) - 3pts
- 🔮 Vision model (Qwen2.5-VL) for image analysis - 8pts
- 🔮 Code assistant (Qwen2.5-Coder) routing - 5pts
- 🔮 Audio transcription (Whisper alternative) - Research needed

**Future Phases:** Phase 3/4
- Image/SVG generation
- Linux & Windows support
- Zero-config installer
- Advanced security (encryption, sandboxing)

**See also:**
- [Product Requirements (PRD)](prd/PRD.md)
- [Agile Backlog](prd/BACKLOG.md)
- [Project Status Report](prd/PROJECT_STATUS.md)
- [Bug Fixes Report](prd/BUG_FIXES_REPORT.md)
- [Coherence Analysis](prd/COHERENCE_ANALYSE.md)
