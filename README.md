**AItao - Your Free, Private, Local AI Assistant**    
   
***"Your data stays yours. No cloud. No compromise."***  

---

## Two Editions

| | **AItao Core** (Free) | **AItao Premium** (Paid) |
|---|---|---|
| **License** | AGPL v3 — open source | Commercial — activated by license key |
| **Price** | Free forever | One-time purchase, no subscription |
| **Local RAG** — index your files, search, chat | ✓ | ✓ |
| **Works with any Ollama model** | ✓ | ✓ |
| **Dashboard & CLI** | ✓ | ✓ |
| **Virtual LLMs** (`-context`, `-basic`) — RAG routing by model name | — | ✓ |
| **Advanced OCR** (PaddleOCR, Qwen-VL for scanned documents) | — | ✓ |
| **Document translation** (fr ↔ zh, en ↔ fr…) | — | ✓ |
| **Personal assistant** (time management, reminders) | — | ✓ |
| **Auto-categorization** of indexed documents | — | ✓ |
| **Priority support** | — | ✓ |

> **Not sure which edition you need?** Start with Core — it already covers 90% of personal RAG use cases.
> Upgrade to Premium when you need the Virtual LLMs or OCR on scanned documents.

---

**Why AItao?**  
**Concerned about privacy?** Every question you ask cloud AI services is stored on their servers. With AItao,  **everything runs on YOUR ** **Computer**. Your documents, your questions, your answers - nothing ever leaves your computer.  
**Want a more ecological approach?** Cloud AI data centers consume enormous amounts of energy. Running AI locally on your computer is significantly more energy-efficient. Yes, it's a bit slower - but it's  **better for the planet**.  
**Need an AI that actually knows YOUR stuff?** Unlike generic AI assistants, AItao  **indexes your personal documents** - PDFs, Word files, text files, code, and more. Keep it in a local database, known only by you.  
 When you ask a question, AItao can searches through YOUR files to give you contextual, relevant answers.  
**AItao uses the power of your own computer.**  
 **  
 It's sometimes a little slower than an online AI,** ** ** **but in return you gain: a reduced environmental impact, privacy, and freedom.**  
**You can choose your own chat interraction interface. AItao works well with **OnlyOffice Agent AI ** or **OpenWebUI|LocalAi|Chainlit  
**What Can AItao Do?**  
**🔍 ** **Smart Search Across All Your Files**  
Ask questions in natural language and find information buried in your documents:  
- *"What was the deadline mentioned in the contract?"*  
- *"Find all references to the Q3 budget"*  
- *"Where did I save that recipe for apple pie?"*  
**💬 ** **Chat With Your Personal AI**  
Have a conversation with an AI that:  
- Knows the contents of your indexed documents  
- Speaks your language (French, English, Chinese, and more)  
- Remembers context during your conversation  
**📄 ** **Organize Your Digital Life**  
- **40+ file types supported**: PDF, DOCX, TXT, Markdown, source code, and more  
- **Automatic indexing**: New files are detected and indexed automatically  
- **Smart categorization** (coming soon): Documents are organized by type  

--- 

**Requirements**  
Before you start, make sure you have:  
| | |  
|-|-|  
| **What** | **Why** |   
| **Windows 11 i64/arm64, ** **macOS 13+** (Ventura or later) | Required for Apple's native features |   
| **8GB RAM** (16GB recommended) | AI models need memory to run |   
| **20GB free disk space** (your choice) | For AI models and document index |   
| **Apple Silicon** (M1/M2/M3) or  **Intel** | Runs on both, faster on Apple Silicon |   
   
--- 
**Installation**  
**Step ** **0** **: ** **For Mac OS, ** **Install Homebrew (** **it’s easier and safe** **)**  
Homebrew is the easiest way to install software on Mac. Open **Terminal** (find it in Applications → Utilities) and paste:  
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"  
   
**Step 1: For Windows 11**  
Unzip the download archive with teh last release. And double clic on   
 ```  
 setup.bat  
 ```  
**Step 2: Install Required Software**  
# Install Python (we need version 3.10 or newer)  
 brew install python@3.13  
   
 # Install Meilisearch (the search engine)  
 brew install meilisearch  
   
 # Install Ollama (the AI engine)  
 brew install ollama  
   
**Step 3: Download an AI Model**  
AItao works with any Ollama-compatible model. We recommend starting with:  
# Download a good general-purpose model (about 4GB)  
 ollama pull llama3.1:8b  
   
 # Or for coding questions, use:  
 ollama pull qwen2.5-coder:7b  
   
***📖 Migrating from GGUF files?*** * If you previously used local GGUF model files,*  
 *  
 see our *[ *Migration Guide* * for the transition to Ollama.*](docs/MIGRATION_MODELS.md "docs/MIGRATION_MODELS.md")  
**Step 4: Install AItao**  
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
   
**Step 5: Configure Your Identity and Folders**  
Edit the configuration file:  
nano config/config.yaml  
   
***5a. Tell AItao who you are (highly recommended)***  
These two fields are injected as the very first system context on **every** conversation, before any document context. This allows all LLMs to adapt their tone, language and cultural references to you.  
# Describe how AItao should present itself  
 who_is_Aitao: "I am AItao, a local AI assistant designed to help you search  
                and interact with your personal documents."  
   
 # A short description of yourself (nationality, location, age, languages…)  
 who_are_you: "I am a French developer living in France, 35 years old."  
   
***Why does this matter?***  
 *  
 Without this context, each LLM answers from scratch with no idea who you are.*  
 *  
 Filling these fields makes responses noticeably more relevant and personal.*  
***5b. Tell AItao which folders to index***  
Find the include_paths section and add your folders:  
indexing:  
   include_paths:  
     - ~/Documents  
     - ~/Desktop  
     - ~/Projects  
   
Save and exit (Ctrl+O, Enter, Ctrl+X).  
**Step 6: Verify Everything Works**  
./aitao.sh status  
   
 # Full validation (unit + e2e + functional)  
 ./aitao.sh validate  
   
You should see all services marked with ✓.  

---

**Using AItao**  
**Starting and Stopping**  
# Start AItao (starts all services)  
 ./aitao.sh start  
   
 # Stop AItao  
 ./aitao.sh stop  
   
 # Restart AItao  
 ./aitao.sh restart  
   
 # Check if everything is running  
 ./aitao.sh status  
   
**Searching Your Documents**  
# Search for something  
 ./aitao.sh search "budget report 2025"  
   
 # Search with filters  
 ./aitao.sh search "invoice" --path ~/Documents/Finance  
   
**Chatting With Your AI**  
# Start an interactive chat session  
 ./aitao.sh chat  
   
Then just type your questions! The AI will search your indexed documents to give you informed answers.  
**Chat Commands:**  
- Type /quit to exit  
- Type /clear to start a new conversation  
- Type /context on to see which documents the AI is using  
- Type /help for all commands  
**Indexing New Documents**  
# Manually index a specific file  
 ./aitao.sh index file ~/Documents/important.pdf  
   
 # Scan all configured folders for new files  
 ./aitao.sh scan run  
   
 # Check indexing progress  
 ./aitao.sh queue status  
   
---
 
**Dashboard — See Everything at a Glance**  
./aitao.sh dashboard  
   
The dashboard gives you a **complete snapshot** of what is happening inside AiTao,  
   
 without having to run several commands one by one.  
**What You See**  
╔══════════════════════════════════════════════════════════════════╗  
 ║  AiTao Dashboard  —  v2.7.0  —  11 Mar 2026  09:15             ║  
 ╚══════════════════════════════════════════════════════════════════╝  
   
 ■ Services                          ■ Modèles Ollama en mémoire  
   ✓ AiTao API    localhost:8200       ✓ llama3.1-local   4 700 MB  (expire dans 2 min)  
   ✓ Meilisearch  localhost:7700       ✓ nomic-embed-text   274 MB  (expire dans 9 min)  
   ✓ Ollama       localhost:11434        (OpenWebUI et OnlyOffice masqués si non actifs)  
   
 ■ Index                             ■ Worker / Scan  
   Meilisearch   12 483 docs           ◌ Worker en veille (PID 1234)  
   LanceDB       12 312 vecteurs         En attente         0  
   12 312/12 483 docs vectorisés (98%)   En cours           0  
   → ./aitao.sh scan run                 Complétés (≠ docs indexés)   1 482  
      puis ./aitao.sh start              Échoués             12  
   Sources : 3 dossier(s) configuré(s)   → ./aitao.sh queue retry  
     ~/Downloads/_sources/                  puis ./aitao.sh start  
     ~/Documents/  
     ~/pCloudSync/_Business/  
   
**Understanding Meilisearch vs LanceDB**  
You will notice two different document counts in the Index section. Here is what they mean:  
| | | |  
|-|-|-|  
|   | **Meilisearch** | **LanceDB** |   
| **What it stores** | The text of your documents, word by word | A mathematical "fingerprint" of the meaning of each document chunk |   
| **How it searches** | Finds exact words and typos: "budget 2025" | Understands meaning: "money report this year" finds the same thing |   
| **Why the count differs** | Every indexed document is here | Only documents that have been through the AI embedding step — this can lag slightly behind |   
   
**In short:** Meilisearch = fast keyword search. LanceDB = smart semantic search.  
   
 Both work together: AiTao first finds semantically similar chunks (LanceDB), then refines the results with keyword filtering (Meilisearch).  
If the counts differ by a lot, the worker is probably still catching up — check the Worker section.  
**Errors Explained**  
The dashboard shows two types of indexing failures:  
- **Format errors** (shown in yellow) — AiTao does not yet know how to read this file type (e.g. .epub, .mobi). These will be retried automatically once support is added.  **No action required.**  
- **Content errors** (shown in red) — The file is corrupted, password-protected, or scanned without OCR text. Open the file directly to investigate.  
If there are failed queue items, re-process them with:  
./aitao.sh queue retry  
 ./aitao.sh start  

---

**Connecting External Tools**  
AItao provides a REST API that works with popular AI tools.  
**API Endpoints**  
| | |  
|-|-|  
| **Endpoint** | **What It Does** |   
| http://localhost:8200/api/health | Check if AItao is running |   
| http://localhost:8200/api/search | Search your documents |   
| http://localhost:8200/api/chat | Chat (Ollama format) |   
| http://localhost:8200/v1/chat/completions | Chat (OpenAI format) |   
| http://localhost:8200/v1/models | List available AI models |   
| http://localhost:8200/docs | Interactive API documentation |   
   
**Setting Up Continue.dev (VS Code Extension)**  
[Continue is a free VS Code extension for AI-assisted coding.](https://continue.dev/ "https://continue.dev/")  
1. Install the Continue extension in VS Code  
2. Open Continue settings (click the gear icon)  
3. Configure it to use AItao:  
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
   
Now Continue will use your local AI enhanced with your indexed documents!  
**Setting Up AnythingLLM**  
[AnythingLLM is a desktop app for chatting with AI.](https://anythingllm.com/ "https://anythingllm.com/")  
1. Open AnythingLLM → Settings → LLM Preference  
2. Select **"Custom OpenAI Compatible"**  
3. Configure:  
- **Base URL**: http://localhost:8200/v1  
- **Model**: llama3.1:8b  
- **API Key**: not-needed (put anything, it's not checked)  
**Setting Up Open WebUI**  
[Open WebUI provides a ChatGPT-like interface.](https://openwebui.com/ "https://openwebui.com/")  
1. Open WebUI settings  
2. Add a new OpenAI-compatible provider:  
- **API Base**: http://localhost:8200/v1  
- **API Key**: any-value  
**Setting Up OnlyOffice AI**  
OnlyOffice AI can use AItao directly as an OpenAI-compatible provider.  
Two plugins are available — use the correct provider type for each:  
| | | | |  
|-|-|-|-|  
| **Plugin** | **Provider type** | **URL** | **Key** |   
| Classic AI Assistant (DD007) | OpenAI | http://127.0.0.1:8200/v1 | sk-local |   
| AI Agent sidebar (DD777) | **OpenAI Compatible** | http://127.0.0.1:8200/v1 | sk-local |   
   
*⚠️ In the AI Agent sidebar, use * ***"OpenAI Compatible"*** *, NOT "OpenAI" — the OpenAI type*  
 *  
 filters models to only GPT-5.2 which blocks all local models.*  
For a full, reproducible local MVP setup (including RAG checks and troubleshooting),  
   
 see [OnlyOffice Integration Guide.](docs/ONLYOFFICE_INTEGRATION.md "docs/ONLYOFFICE_INTEGRATION.md")  

---

**Managing AI Models**  
AItao uses [Ollama as its AI engine. Models are managed through Ollama and configured in AItao.](https://ollama.ai/ "https://ollama.ai/")  
**Viewing Available Models**  
# See all Ollama models and their status in AItao  
 ./aitao.sh models status  
   
**Adding a New Model**  
# Add a model (automatically downloads from Ollama if needed)  
 ./aitao.sh models add mistral:7b --role chat  
   
 # Add without downloading (if you already have it)  
 ./aitao.sh models add llama3.1:8b --role chat --no-pull  
   
 # Mark a model as required for AItao to function  
 ./aitao.sh models add qwen2.5-coder:7b --role code --required  
   
**Available Roles:**  
- chat - General conversation  
- code - Code generation and analysis  
- embedding - Document embeddings (for search)  
**Removing a Model**  
# Remove from AItao config only (keeps model in Ollama)  
 ./aitao.sh models remove mistral:7b  
   
 # Also delete from Ollama to free disk space  
 ./aitao.sh models remove mistral:7b --delete-ollama  
   
 # Force removal without confirmation  
 ./aitao.sh models remove mistral:7b --force  
   
**Recommended Models**  
| | | | |  
|-|-|-|-|  
| **Use Case** | **Model** | **Size** | **Command** |   
| General chat | llama3.1:8b | 4.7GB | ollama pull llama3.1:8b |   
| Coding | qwen2.5-coder:7b | 4.7GB | ollama pull qwen2.5-coder:7b |   
| Fast responses | llama3.2:3b | 2.0GB | ollama pull llama3.2:3b |   
| Embeddings | nomic-embed-text | 274MB | ollama pull nomic-embed-text |   
   
---
 
**Complete Command Reference**  
**Service Management**  
| | |  
|-|-|  
| **Command** | **What It Does** |   
| ./aitao.sh start | Start all AItao services |   
| ./aitao.sh stop | Stop all AItao services |   
| ./aitao.sh restart | Restart all services |   
| ./aitao.sh status | Quick service health check |   
| ./aitao.sh dashboard | **Full dashboard** — services, models, index, errors |   
   
**Document Operations**  
| | |  
|-|-|  
| **Command** | **What It Does** |   
| ./aitao.sh scan run | Scan folders for new files |   
| ./aitao.sh scan status | Show scan statistics |   
| ./aitao.sh index file <path> | Index a specific file |   
| ./aitao.sh queue status | Show indexing queue status |   
| ./aitao.sh queue list | List pending files |   
   
**Search & Chat**  
| | |  
|-|-|  
| **Command** | **What It Does** |   
| ./aitao.sh search "<query>" | Search your documents |   
| ./aitao.sh chat | Start interactive chat |   
   
**Infrastructure**  
| | |  
|-|-|  
| **Command** | **What It Does** |   
| ./aitao.sh ms status | Meilisearch status |   
| ./aitao.sh ms start | Start Meilisearch only |   
| ./aitao.sh ms stop | Stop Meilisearch only |   
| ./aitao.sh db status | LanceDB vector database status |   
| ./aitao.sh worker status | Background worker status |   
| ./aitao.sh worker start | Start background worker |   
| ./aitao.sh worker stop | Stop background worker |   
   
**Configuration**  
| | |  
|-|-|  
| **Command** | **What It Does** |   
| ./aitao.sh config show | Display current configuration |   
| ./aitao.sh config validate | Check config file for errors |   
| ### Help System |   |   
   
Every command group has built-in help with practical examples:  
| | |  
|-|-|  
| **Command** | **What It Does** |   
| ./aitao.sh help | Overview of all commands with situational guide |   
| ./aitao.sh queue help | File queue management with examples |   
| ./aitao.sh scan help | Folder scanner with examples |   
| ./aitao.sh worker help | Background worker with examples |   
| ./aitao.sh ms help | Meilisearch management with examples |   
| ./aitao.sh db help | LanceDB vector database with examples |   
| ./aitao.sh search help | Hybrid search operations with examples |   
| ./aitao.sh index help | Indexing pipeline with examples |   
   
---

**"Command not found: aitao.sh"**  
Make sure you're in the AItao folder and the script is executable:  
cd ~/aitao  # or wherever you installed it  
 chmod +x aitao.sh  
 ./aitao.sh status  
   
**"Meilisearch is not running"**  
Start Meilisearch manually:  
brew services start meilisearch  
   
**"Ollama is not running"**  
Start Ollama:  
ollama serve  
   
**"No models available"**  
Download a model:  
ollama pull llama3.1:8b  
   
**"Port 8200 already in use"**  
Another application is using the port. Either stop that application or change the port in config/config.yaml.  
**"Search returns no results"**  
Make sure your documents are indexed:  
./aitao.sh scan run  
 ./aitao.sh queue status  # Wait until queue is empty  
   
---

**Supported File Types**  
AItao can index these file types:  
| | |  
|-|-|  
| **Category** | **Extensions** |   
| **Documents** | .pdf, .docx, .doc, .txt, .rtf, .odt |   
| **Markdown** | .md, .markdown, .rst |   
| **Code** | .py, .js, .ts, .java, .c, .cpp, .go, .rs, .rb, .php, .swift, .kt |   
| **Data** | .json, .yaml, .yml, .xml, .csv, .toml |   
| **Web** | .html, .htm, .css |   
| **LaTeX** | .tex, .bib |   
   
---
 
**Getting Help**  
- **Built-in CLI help**: Run ./aitao.sh help for a quick situational guide, or ./aitao.sh <group> help (e.g. ./aitao.sh queue help) for detailed examples on any command group.  
- **Documentation**: Check the docs/ folder for detailed guides  
- **Issues**: Report bugs on [GitHub Issues](https://github.com/shamantao/aitao/issues "https://github.com/shamantao/aitao/issues")  
- **Configuration**: See prd/PRD.md for technical details  

---

**What's New**  
**v2.7.0 — March 2026**  
**CLI startup performance — 18× faster**  
   
 Help commands now load in ~0.2 seconds (down from 3.6 s). Heavy AI libraries (sentence-transformers, lancedb) are now loaded lazily — only when actually needed for indexing, not on every command invocation.  
**Built-in help for every command group**  
   
 All major groups now expose contextual help with practical examples:  
./aitao.sh help            # Situational guide (start here when lost)  
 ./aitao.sh queue help      # Queue management & retry failed files  
 ./aitao.sh scan help       # Folder scanner  
 ./aitao.sh worker help     # Background worker  
 ./aitao.sh ms help         # Meilisearch engine  
 ./aitao.sh search help     # Hybrid search (semantic + fulltext)  
   
**Dashboard improvements**  
- Optional services (OpenWebUI, OnlyOffice) are hidden when not running — no more spurious ✗  
- Worker now has 3 states: en cours (green) / en veille (yellow, idle) / arrêté (red)  
- Index section shows vectorisation ratio: 12 312/12 483 docs vectorisés (98%)  
- Actionnable hints on errors and sync gaps: exact commands to copy-paste  
**v2.6.0 — March 2026**  
- CLI dashboard ./aitao.sh dashboard (US-044)  
- Config migrated from YAML to TOML (US-045)  
- Windows portable distribution + auto-update (US-034b, US-036, US-038, US-046)  

---

## License

**AItao Core** is open source under the **GNU Affero General Public License v3 (AGPL-3.0)**.

This means:
- ✓ Free to use, study, and modify for personal use
- ✓ No data leaves your machine — ever
- ✓ You can redistribute it, but modifications must also be AGPL
- ✗ You cannot bundle AItao in a closed-source commercial product without a commercial license

**AItao Premium** is distributed under a separate **Commercial License**, activated by a license key
purchased on [shamantao.com](https://shamantao.com). One key = one machine, perpetual use,
no subscription. Includes all Core features + premium modules.

For commercial use of the Core code without AGPL obligations, contact: **license@shamantao.com**

Full license text: [LICENSE](LICENSE)

---

<p align="center">
  <strong>AItao</strong> — Your Personal AI, Your Privacy, Your Planet 🌍
</p>
