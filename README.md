# AItao - Your Free, Private, Local AI Assistant

<p align="center">
  <img src="docs/images/aitao-logo.png" alt="AItao Logo" width="200" />
</p>

> **"Your data stays yours. No cloud. No subscription. No compromise."**

---

## Why AItao?

**Tired of paying for AI?** ChatGPT, Claude, and other cloud AI services cost money every month. AItao is **100% free** to use forever.

**Concerned about privacy?** Every question you ask cloud AI services is stored on their servers. With AItao, **everything runs on YOUR Mac**. Your documents, your questions, your answers - nothing ever leaves your computer.

**Want a more ecological approach?** Cloud AI data centers consume enormous amounts of energy. Running AI locally on your Mac is significantly more energy-efficient. Yes, it's a bit slower - but it's **better for the planet**.

**Need an AI that actually knows YOUR stuff?** Unlike generic AI assistants, AItao **indexes your personal documents** - PDFs, Word files, text files, code, and more. When you ask a question, AItao searches through YOUR files to give you contextual, relevant answers.

---

## What Can AItao Do?

### 🔍 **Smart Search Across All Your Files**
Ask questions in natural language and find information buried in your documents:
- *"What was the deadline mentioned in the contract?"*
- *"Find all references to the Q3 budget"*
- *"Where did I save that recipe for apple pie?"*

### 💬 **Chat With Your Personal AI**
Have a conversation with an AI that:
- Knows the contents of your indexed documents
- Speaks your language (French, English, Chinese, and more)
- Remembers context during your conversation

### 📄 **Organize Your Digital Life**
- **40+ file types supported**: PDF, DOCX, TXT, Markdown, source code, and more
- **Automatic indexing**: New files are detected and indexed automatically
- **Smart categorization** (coming soon): Documents are organized by type

---

## Requirements

Before you start, make sure you have:

| What | Why |
|------|-----|
| **macOS 13+** (Ventura or later) | Required for Apple's native features |
| **8GB RAM** (16GB recommended) | AI models need memory to run |
| **20GB free disk space** | For AI models and document index |
| **Apple Silicon** (M1/M2/M3) or Intel | Runs on both, faster on Apple Silicon |

---

## Installation

### Step 1: Install Homebrew (if you don't have it)

Homebrew is the easiest way to install software on Mac. Open **Terminal** (find it in Applications → Utilities) and paste:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Required Software

```bash
# Install Python (we need version 3.10 or newer)
brew install python@3.13

# Install Meilisearch (the search engine)
brew install meilisearch

# Install Ollama (the AI engine)
brew install ollama
```

### Step 3: Download an AI Model

AItao works with any Ollama-compatible model. We recommend starting with:

```bash
# Download a good general-purpose model (about 4GB)
ollama pull llama3.1:8b

# Or for coding questions, use:
ollama pull qwen2.5-coder:7b
```

### Step 4: Install AItao

```bash
# Install uv (Python package manager - very fast!)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Download AItao
git clone https://github.com/shamantao/aitao.git
cd aitao

# Set up the environment
uv venv
source .venv/bin/activate
uv pip install -e .

# Run the installation script
./install.sh
```

### Step 5: Configure Your Folders

Edit the configuration file to tell AItao which folders to index:

```bash
nano config/config.yaml
```

Find the `include_paths` section and add your folders:

```yaml
indexing:
  include_paths:
    - ~/Documents
    - ~/Desktop
    - ~/Projects
```

Save and exit (Ctrl+O, Enter, Ctrl+X).

### Step 6: Verify Everything Works

```bash
./aitao.sh status
```

You should see all services marked with ✓.

---

## Using AItao

### Starting and Stopping

```bash
# Start AItao (starts all services)
./aitao.sh start

# Stop AItao
./aitao.sh stop

# Restart AItao
./aitao.sh restart

# Check if everything is running
./aitao.sh status
```

### Searching Your Documents

```bash
# Search for something
./aitao.sh search "budget report 2025"

# Search with filters
./aitao.sh search "invoice" --path ~/Documents/Finance
```

### Chatting With Your AI

```bash
# Start an interactive chat session
./aitao.sh chat
```

Then just type your questions! The AI will search your indexed documents to give you informed answers.

**Chat Commands:**
- Type `/quit` to exit
- Type `/clear` to start a new conversation
- Type `/context on` to see which documents the AI is using
- Type `/help` for all commands

### Indexing New Documents

```bash
# Manually index a specific file
./aitao.sh index file ~/Documents/important.pdf

# Scan all configured folders for new files
./aitao.sh scan run

# Check indexing progress
./aitao.sh queue status
```

---

## Connecting External Tools

AItao provides a REST API that works with popular AI tools.

### API Endpoints

| Endpoint | What It Does |
|----------|--------------|
| `http://localhost:8200/api/health` | Check if AItao is running |
| `http://localhost:8200/api/search` | Search your documents |
| `http://localhost:8200/api/chat` | Chat (Ollama format) |
| `http://localhost:8200/v1/chat/completions` | Chat (OpenAI format) |
| `http://localhost:8200/v1/models` | List available AI models |
| `http://localhost:8200/docs` | Interactive API documentation |

### Setting Up Continue.dev (VS Code Extension)

[Continue](https://continue.dev/) is a free VS Code extension for AI-assisted coding.

1. Install the Continue extension in VS Code
2. Open Continue settings (click the gear icon)
3. Configure it to use AItao:

```json
{
  "models": [
    {
      "title": "AItao (Local RAG)",
      "provider": "openai",
      "model": "llama3.1:8b",
      "apiBase": "http://localhost:8200/v1"
    }
  ]
}
```

Now Continue will use your local AI enhanced with your indexed documents!

### Setting Up AnythingLLM

[AnythingLLM](https://anythingllm.com/) is a desktop app for chatting with AI.

1. Open AnythingLLM → Settings → LLM Preference
2. Select **"Custom OpenAI Compatible"**
3. Configure:
   - **Base URL**: `http://localhost:8200/v1`
   - **Model**: `llama3.1:8b`
   - **API Key**: `not-needed` (put anything, it's not checked)

### Setting Up Open WebUI

[Open WebUI](https://openwebui.com/) provides a ChatGPT-like interface.

1. Open WebUI settings
2. Add a new OpenAI-compatible provider:
   - **API Base**: `http://localhost:8200/v1`
   - **API Key**: `any-value`

---

## Complete Command Reference

### Service Management

| Command | What It Does |
|---------|--------------|
| `./aitao.sh start` | Start all AItao services |
| `./aitao.sh stop` | Stop all AItao services |
| `./aitao.sh restart` | Restart all services |
| `./aitao.sh status` | Show service health dashboard |

### Document Operations

| Command | What It Does |
|---------|--------------|
| `./aitao.sh scan run` | Scan folders for new files |
| `./aitao.sh scan status` | Show scan statistics |
| `./aitao.sh index file <path>` | Index a specific file |
| `./aitao.sh queue status` | Show indexing queue status |
| `./aitao.sh queue list` | List pending files |

### Search & Chat

| Command | What It Does |
|---------|--------------|
| `./aitao.sh search "<query>"` | Search your documents |
| `./aitao.sh chat` | Start interactive chat |

### Infrastructure

| Command | What It Does |
|---------|--------------|
| `./aitao.sh ms status` | Meilisearch status |
| `./aitao.sh ms start` | Start Meilisearch only |
| `./aitao.sh ms stop` | Stop Meilisearch only |
| `./aitao.sh db status` | LanceDB vector database status |
| `./aitao.sh worker status` | Background worker status |
| `./aitao.sh worker start` | Start background worker |
| `./aitao.sh worker stop` | Stop background worker |

### Configuration

| Command | What It Does |
|---------|--------------|
| `./aitao.sh config show` | Display current configuration |
| `./aitao.sh config validate` | Check config file for errors |

---

## Troubleshooting

### "Command not found: aitao.sh"

Make sure you're in the AItao folder and the script is executable:
```bash
cd ~/aitao  # or wherever you installed it
chmod +x aitao.sh
./aitao.sh status
```

### "Meilisearch is not running"

Start Meilisearch manually:
```bash
brew services start meilisearch
```

### "Ollama is not running"

Start Ollama:
```bash
ollama serve
```

### "No models available"

Download a model:
```bash
ollama pull llama3.1:8b
```

### "Port 8200 already in use"

Another application is using the port. Either stop that application or change the port in `config/config.yaml`.

### "Search returns no results"

Make sure your documents are indexed:
```bash
./aitao.sh scan run
./aitao.sh queue status  # Wait until queue is empty
```

---

## Supported File Types

AItao can index these file types:

| Category | Extensions |
|----------|------------|
| **Documents** | .pdf, .docx, .doc, .txt, .rtf, .odt |
| **Markdown** | .md, .markdown, .rst |
| **Code** | .py, .js, .ts, .java, .c, .cpp, .go, .rs, .rb, .php, .swift, .kt |
| **Data** | .json, .yaml, .yml, .xml, .csv, .toml |
| **Web** | .html, .htm, .css |
| **LaTeX** | .tex, .bib |

---

## Getting Help

- **Documentation**: Check the `docs/` folder for detailed guides
- **Issues**: Report bugs on [GitHub Issues](https://github.com/shamantao/aitao/issues)
- **Configuration**: See `prd/PRD.md` for technical details

---

## License

MIT License - Free to use, modify, and distribute.

---

<p align="center">
  <strong>AItao</strong> - Your Personal AI, Your Privacy, Your Planet 🌍
</p>
