# AItao V2 - Local-First Document Search & Translation Engine

> *"Your data are your own. What happens on your Mac, stays on your Mac."*

A privacy-focused document search and translation system that runs entirely on your local machine. No API keys, no cloud dependencies, no data leaving your computer.

## Features

- 🔍 **Hybrid Search**: Combines full-text (Meilisearch) + semantic (LanceDB) search
- 📄 **Document Extraction**: PDF, DOCX, TXT, Markdown, and 40+ code file types
- 🌐 **Translation Ready**: Traditional Chinese → French/English (Sprint 5)
- 🔒 **100% Local**: All processing happens on your machine
- ⚡ **Fast**: Optimized for Apple Silicon Macs

## Requirements

- macOS 13+ (Ventura or later)
- Python 3.10+
- [Meilisearch](https://www.meilisearch.com/) running locally
- 8GB+ RAM recommended

## Installation

### 1. Install uv (Package Manager)

We use `uv` for fast, reproducible dependency management:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/shamantao/aitao.git
cd aitao

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

### 3. Install and Start Meilisearch

```bash
# Install via Homebrew
brew install meilisearch

# Start Meilisearch (runs on localhost:7700)
meilisearch
```

### 4. Configure

```bash
# Copy config template
cp config/config.toml.template config/config.toml

# Edit configuration (paths, settings)
nano config/config.toml
```

### 5. Verify Installation

```bash
# Check all dependencies
python scripts/check_deps.py

# Run status check
./aitao.sh status
```

## Quick Start

```bash
# Activate environment
source .venv/bin/activate

# Index a document
./aitao.sh index file /path/to/document.pdf

# Search (coming in Sprint 2)
./aitao.sh search "your query"

# Check system status
./aitao.sh status
```

## CLI Commands

```bash
# Main commands
./aitao.sh status          # System health dashboard
./aitao.sh test            # Run test suite

# Document management
./aitao.sh extract file <path>    # Extract text from document
./aitao.sh index file <path>      # Index document

# Infrastructure
./aitao.sh ms status       # Meilisearch status
./aitao.sh db status       # LanceDB status

# Background processing
./aitao.sh scan run        # Scan configured paths
./aitao.sh queue status    # View indexing queue
./aitao.sh worker status   # Background worker status
```

## Development

### Running Tests

```bash
# Activate environment
source .venv/bin/activate

# Run all tests (~3-4 minutes)
./aitao.sh test

# Run specific test file
pytest tests/unit/test_lancedb_client.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Adding Dependencies

**Always use `uv`, never raw `pip`:**

```bash
# Install a new package
uv pip install package-name

# Don't forget to add it to pyproject.toml!
```

### Project Structure

```
aitao/
├── src/
│   ├── core/           # PathManager, Logger, Config
│   ├── indexation/     # Scanner, Queue, Worker, Extractors
│   ├── search/         # LanceDB, Meilisearch clients
│   ├── cli/            # Typer CLI commands
│   └── api/            # FastAPI REST endpoints (Sprint 3)
├── config/
│   └── config.toml     # Main configuration
├── scripts/            # Utility scripts
├── tests/              # Test suite
└── prd/                # Product documentation
```

## Roadmap

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 0 | Foundation (Core, DB) | ✅ Complete |
| Sprint 1 | Indexation (Scanner, Queue) | ✅ Complete |
| Sprint 2 | Search API | 🔄 In Progress |
| Sprint 3 | OCR Pipeline | 📋 Planned |
| Sprint 4 | Translation | 📋 Planned |
| Sprint 5 | Dashboard | 📋 Planned |

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

1. Create feature branch from `pdr/v2-remodular`
2. Follow the coding conventions (see `prd/PRD.md`)
3. Ensure all tests pass
4. Submit pull request

---

*AItao V2 - Built with ❤️ for privacy*
