# Product Requirements Document (PRD)
# AI Tao 2.0 - Local-First Search & Translation Engine

**Version:** 2.0  
**Date:** January 28, 2026  
**Status:** Active  
**Author:** shamantao (AI Tao Project)  
**Branch:** `pdr/v2-remodular`

---

## Executive Summary

**AItao** is a local-first, privacy-focused AI assistant that runs entirely on your personal computer. It empowers users to leverage powerful AI capabilities without sacrificing data privacy, environmental sustainability, or paying expensive cloud subscriptions. AItao is the ultimate alternative to cloud-based AI services for users who want to own their data and their intelligence.

**Core Principle:** *"Your data are your own. What happens on your Mac, stays on your Mac."*

**V2 Focus:** A modular, production-ready **document search and translation engine** for personal knowledge management, with priority on Traditional Chinese → English/French translation accuracy, filesystem discovery, and semantic search capabilities.

---

## 1. Vision & Mission

### Vision
Create a **modular, privacy-first knowledge retrieval system** that empowers users to find, understand, and translate documents across their entire filesystem—without sacrificing privacy, speed, or control.

### Mission
Deliver a production-ready tool that:
- Indexes and searches documents semantically (not just keywords)
- Translates Traditional Chinese documents into English/French with high accuracy
- Provides actionable insights (summaries, deadlines, next actions)
- Runs entirely locally on macOS (Apple Silicon M1+)
- Integrates seamlessly with VSCode/Continue, Wave Terminal, and custom UIs

### Core Values
1. **🔒 Absolute Privacy**: Documents never leave the local machine
2. **🧩 Modularity**: Each component (indexer, search, OCR, translation, API) is independent and replaceable
3. **🔧 Maintainability**: Clean code, standard interfaces, comprehensive logging
4. **⚡️ Efficiency**: Optimized for limited resources (Mac laptop, not cloud servers)
5. **💰 Zero Cost**: All models and tools are free and open-source (no API keys)
6. **🎯 Accuracy**: Translation and OCR quality prioritized over speed for critical documents
7. **🔄 Reversibility**: All decisions must be revertable—users can correct categorizations, swap models, change storage

---

## 2. Target Audience & Primary Use Cases

### Primary User Persona: "Multilingual Knowledge Worker"
- **Profile**: Professional managing mixed-language documents (Traditional Chinese, French, English)
- **Pain Points**:
  - Cannot read Chinese but receives important docs (government, business, school)
  - Forgets where files are stored (Dropbox, local drive, external HD, clouds)
  - Spotlight/Finder fails on semantic search ("where's the Germany trip doc from June 2025?")
  - Needs quick answers: "What are the deadlines in this accountant's doc?"
- **Technical Level**: Basic to intermediate (can follow installation guides, edit config files)
- **Success Criteria**: 
  - Find document in <5 seconds with natural language query
  - Get accurate translation + summary in <30 seconds
  - Never expose documents to external services

### Secondary Personas
1. **Developer**: Integrating AItao search into Wave Terminal/VSCode workflows
2. **Archivist**: Managing large collections (photos with EXIF, legacy scanned docs)
3. **Privacy-Conscious Professional**: Lawyer/accountant with confidential files

---

## 3. Critical Use Cases (MVP Priority)

### UC-001: Semantic Document Search
**Priority:** 🔥 **CRITICAL**  
**User Story:**  
> "Where is the document about the Germany trip in June 2025?"

**Expected Behavior:**
1. User enters natural language query (French or English)
2. System searches:
   - **Meilisearch** (full-text + filters: path, date) in parallel with
   - **LanceDB** (semantic vector search)
3. Returns ranked results with:
   - **File path** (clickable, opens file)
   - **Summary**: "This document mentions a trip to Germany scheduled for June 10-15, 2025..."
   - **Confidence score**
4. User clicks → file opens in default app

**Technical Requirements:**
- Query latency: <3 seconds for 500K documents
- Support filters: date range, file path pattern, file type
- Hybrid search: combine full-text + semantic ranking

---

### UC-002: Document Translation & Action Extraction
**Priority:** 🔥 **CRITICAL**  
**User Story:**  
> "The accountant sent me a Chinese document with tasks. What are the deadlines?"

**Expected Behavior:**
1. User uploads/selects Traditional Chinese document (PDF/image/docx)
2. System:
   - **OCR** if needed (Qwen-VL for tables, AppleScript OCR for simple text)
   - **Translates** to French/English using local LLM
   - **Extracts structured data**: deadlines, tasks, action items
3. Returns:
   - Full translation
   - Structured list: "Task 1: Due 2026-02-15 (15 days), Task 2: Due 2026-03-01..."
4. User can correct/categorize document

**Technical Requirements:**
- Translation accuracy: Human-readable, context-aware (not word-for-word)
- Table extraction: Preserve structure (JSON/CSV output)
- Action extraction: Parse dates, amounts, entities

---

### UC-003: Filesystem Scanning & Auto-Indexing
**Priority:** 🚀 **HIGH**  
**User Story:**  
> "Index all my Dropbox and external hard drives daily, notify me of new documents"

**Expected Behavior:**
1. **Daily cronjob** scans configured volumes (`config.yaml`)
2. For each new/modified file:
   - Extract text (direct or OCR)
   - Extract EXIF metadata (images)
   - **Auto-categorize** using LLM (enterprise/school/sports/leisure/news)
   - Add to **indexing queue** (JSON file)
3. **Background worker** processes queue:
   - Simple text files → immediate indexing
   - PDFs/images → queue for OCR (don't interrupt active tasks)
4. User receives summary: "15 new documents indexed, 3 require manual categorization"

**Technical Requirements:**
- Watch filesystem changes (macOS FSEvents or equivalent)
- Queue system: JSON files in `~/Downloads/_sources/aitao/queue/`
- Throttle based on system load (detect user activity)
- Skip temporary/cache files

---

### UC-004: Manual Document Ingestion (UI/CLI)
**Priority:** 🚀 **HIGH**  
**User Story:**  
> "I just received a scanned PDF with tables, ingest it now with Qwen-VL"

**Expected Behavior:**
1. User drags file into UI or runs CLI command:
   ```bash
   aitao ingest /path/to/document.pdf --ocr qwen-vl --priority high
   ```
2. System:
   - Skips queue (high priority)
   - Uses Qwen-VL for OCR + table extraction
   - Returns progress: "Processing... 30% done"
3. On completion:
   - Shows translation + extracted tables
   - Asks: "Categorize this as [enterprise/school/other]?"
   - Indexes into LanceDB + Meilisearch

**Technical Requirements:**
- Real-time progress feedback
- User can cancel/pause
- Priority queue (user requests > background scan)

---

### UC-005: Category Management & Correction
**Priority:** 🔮 **MEDIUM**  
**User Story:**  
> "The system classified a news magazine as 'cooking' because of a recipe. Reclassify it as 'news/international'"

**Expected Behavior:**
1. User searches/browses indexed documents
2. Selects document → "Edit Category"
3. Changes category → system:
   - Updates document metadata
   - **Saves correction** to `corrections.json`
   - **Improves future classification** (feedback loop)
4. Next scan uses learned corrections

**Technical Requirements:**
- User-friendly category picker (dropdown + free text)
- Corrections logged for model fine-tuning (future)
- Re-index document with new metadata

---

### UC-006: RAG Integration (Continue/Wave/Custom UI)
**Priority:** 🚀 **HIGH**  
**User Story:**  
> "Query AItao from VSCode Continue or Wave Terminal"

**Expected Behavior:**
1. External app sends REST API request:
   ```json
   POST /api/search
   {
     "query": "Where is the Germany trip doc?",
     "filters": {"date_after": "2025-01-01"},
     "limit": 5
   }
   ```
2. AItao returns JSON:
   ```json
   {
     "results": [
       {
         "path": "/path/to/doc.pdf",
         "summary": "Trip to Germany...",
         "score": 0.95,
         "date": "2025-06-10"
       }
     ]
   }
   ```
3. Continue/Wave displays results inline

**Technical Requirements:**
- FastAPI REST endpoint (port 5000)
- OpenAPI schema for client generation
- Shared LanceDB/Meilisearch access (no duplication)

---

## 4. Functional Requirements

### FR-001: Configuration Management
- **Single source of truth:** `config.toml` file
- **No GUI configuration:** All settings (volumes, models, preferences) defined in config file
- **Settings include:**
  - Indexed volumes/folders
  - Active AI models
  - Storage limits (500GB default, alerts at 25% increments)
  - Network usage limits (unlimited in V1, configurable in config)
  - Web search opt-in status

### FR-002: CLI Interface (`aitao.sh`)
- **Commands:**
  - `./aitao.sh start` - Start all services (AI engine + UI + sync agent)
  - `./aitao.sh stop` - Gracefully stop all services
  - `./aitao.sh restart` - Restart services
  - `./aitao.sh status` - Check service health
  - `./aitao.sh check [scan|config]` - Validate setup
  - `./aitao.sh help` - Show usage guide
- **Status:** ✅ In Progress

### FR-003: RAG (Retrieval-Augmented Generation)
- **Vector Database:** LanceDB (single source of truth)
- **Indexing orchestration:** Sync Agent surveils `include_paths`, envoie les fichiers vers le pipeline d'extraction (texte direct ou OCR), puis insère dans LanceDB
- **Access pattern:** 
  - UI users: via l'UI choisie (optionnelle)
  - External apps: via RAG Server API (port 8200, model-agnostic)
- **Supported file types:**
  - Documents: .txt, .md, .docx, .odt
  - Presentations: .odp, .pptx
  - PDFs (text or scanned)
  - Images: .jpg, .png, .webp
  - Code: .py, .js, .ts, .cpp, .java, etc.
  - Audio/Video: basique (métadonnées), OCR pour contenus image/scans
- **Metadata extraction:** File paths, modification dates, SHA-256 hash (integrity), source/ocr engine used
- **Retention policy:** Storage limit-based (not time-based)—oldest/least-used data purged when approaching 500GB limit

### FR-004: Web Search (Opt-in)
- **User consent required:** Explicit checkbox or confirmation
- **Search Engine:** DuckDuckGo (privacy-respecting, no tracking)
- **Privacy safeguards:**
  - Queries not logged online
  - Results stored locally only
  - User decides whether to index results into private RAG
- **Citation style:** Perplexity-like source attribution
- **Status:** ✅ Core Implementation Done (DuckDuckGo scraper in `web.py`), UI Integration TODO

### FR-005: AnythingLLM Integration
- **Deployment:** Docker container
- **Sync Agent (`sync_agent.py`):** Automatically creates Workspaces from `config.toml` volumes
- **UI Access:** Browser-based (default `http://localhost:3001`)
- **Status:** ✅ AnythingLLM Done, Sync Agent In Progress

### FR-006: Vision & OCR Routing
- **OCR engines:** `easyocr` (léger, rapide texte simple) et `qwen-vl` (multimodal, extraction de tableaux)
- **OCR router (`pipe_router`):** module léger (pdfminer/pypdf + OpenCV) qui détecte présence de texte existant et probabilité de tableaux, puis route vers l’OCR approprié ; évite d’exécuter Qwen-VL quand EasyOCR suffit. Les seuils (aire table, intersections, densité) sont configurables dans `config.toml` (section dédiée bas de fichier).
- **Pre-downloaded models available:**
  - `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` (text generation)
  - `qwen2.5-coder-7b-instruct-q4_k_m.gguf` (code assistance)
  - `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` (vision/multimodal)
- **Use cases:**
  - OCR from scanned PDFs/images (auto routing)
  - Table extraction (PDF/image → JSON/CSV/Excel) via Qwen-VL lorsqu’un tableau est détecté
  - Image description and translation
- **Status:** 🔄 Models downloaded; inspector + routing to be integrated

### FR-007: Image/SVG Generation
- **Approach:** Open-source models (Flux, Stable Diffusion) or specialized SVG prompting
- **Output formats:** SVG (preferred), PNG, other open formats
- **Status:** 📋 TODO

### FR-008: Audio/Video Transcription
- **V1 Scope:** Not Whisper—explore alternative open-source solutions
- **Use cases:**
  - Extract transcriptions from mp4/mp3 in watched folders
  - Subtitle resynchronization
- **Status:** 📋 TODO (Alternative to Whisper)

### FR-009: Model Management
- **Source:** HuggingFace open-source models
- **Installation:** AI Tao can propose and download models
- **Inference Engine:** `llama-cpp-python` (OpenAI-compatible API)
- **Modularity:** Models are swappable "Lego blocks"

### FR-010: Conversation History
- **Storage:** Local only
- **User control:** Ability to delete conversation history (retention/forget)
- **UI:** Accessible via AnythingLLM interface

---

## 5. Non-Functional Requirements

### NFR-001: Platform Support
- **V1 Priority:** macOS (first-class support)
- **Future:** Linux and Windows compatibility
- **Architecture:** Cross-platform Python core + Bash orchestration (macOS/Linux), PowerShell (Windows future)

### NFR-002: Performance & Resources
- **Execution:** Asynchronous CPU/GPU/RAM utilization
- **Latency:** To be measured and optimized based on user experience
- **Resource Requirements:** User must have computer capable of running selected AI models (varies by model size)

### NFR-003: Storage
- **Default Limit:** 500GB
- **Alerts:** Notify user at 25% increments (125GB, 250GB, 375GB, 500GB)
- **Configurable:** Via `config.toml`
- **Retention:** Oldest/least-used data purged when approaching limit

### NFR-004: Network Usage
- **Principle:** Offline-first
- **V1 Limitation:** Unlimited (no throttling)
- **Future:** Configurable in `config.toml`
- **Web Search:** Explicit opt-in only, no background telemetry

### NFR-005: Security & Privacy
- **Logs:** Local storage only, never uploaded
- **Encryption:** Not implemented in V1 (future consideration)
- **Sandboxing:** Not implemented in V1 (to be clarified)
- **Audit Policies:** Not implemented in V1 (to be clarified)
- **Data Ownership:** 100% local, user retains full control

### NFR-006: Modularity
- **Architecture:** Lego-block design
- **Swappable Components:**
  - AI models
  - UI frontends (AnythingLLM, custom)
  - Inference engines
  - Vector databases
  - Open-source frameworks/agents
- **Dependency Management:** Prefer open-source, free, secure, popular libraries

### NFR-007: Error Tolerance & UX
- **Latency Target:** To be defined based on user testing
- **Error Handling:** Graceful degradation, clear error messages
- **Metrics Collection:** System to measure quality and make data-driven decisions

### NFR-008: Build & Tooling
- **uv-first workflow:** Manage and lock Python dependencies with `uv` (install, run, and sync). Do not rely on raw `pip` in scripts.
- **Centralized paths:** All file system locations are derived through `path_manager` using `config.toml`. No hard-coded absolute paths in source code.
- **Centralized logging:** Use the shared logger utility; logs live under the configured logs directory.

---

## 6. Technical Architecture

### 6.1 Stack
- **Language:** Python 3.14 (core engine), Bash (orchestration)
- **Inference Engine:** `llama-cpp-python` (OpenAI-compatible server)
- **Vector Database:** LanceDB
- **UI Framework:** AnythingLLM (Docker)
- **Configuration:** TOML (single `config.toml` file)
 - **Dependency Manager:** uv (Astral) — all Python dependencies are installed and executed via `uv`; avoid raw `pip`/manual venv usage
   - Path policy: never hard-code absolute paths; always resolve through `path_manager` and `config.toml`

### 6.2 Key Components
1. **aitao.sh** - CLI orchestrator (start/stop/status)
2. **config.toml** - Single source of truth for all settings
3. **sync_agent.py** - Bridge between file system and AnythingLLM (auto-creates Workspaces, watches folders)
4. **Inference Server** (Port 8247) - `llama-cpp-python` serving OpenAI-compatible API (`/v1/chat/completions`)
5. **RAG Server** (Port 8200) - Generic RAG query endpoint (`/v1/rag/search`) decoupled from AnythingLLM
6. **AnythingLLM** (Port 3001) - Docker-based UI for chat, workspace management, and indexing orchestration
7. **AnythingLLM SQLite DB** - Single source of truth for documents, embeddings, vectors (shared by UI and external apps)

### 6.3 Architecture Principle: Model Independence
**Critical Design Principle:** AI Tao is **model-agnostic** and **UI-agnostic**.

- **Apps choose their model:** Wave Terminal can use `qwen-coder`, VSCode can use `llama3.1-8b`. AnythingLLM's UI model choice is irrelevant.
- **Apps share RAG data:** All apps query the same AnythingLLM DB for documents. Sync Agent is the single ingestion point.
- **Inference decoupled from UI:** Inference Server (port 8247) is independent—AnythingLLM uses it, but so can external apps.
- **RAG decoupled from AnythingLLM:** RAG Server (port 8200) reads AnythingLLM's DB but is a generic interface, not tied to AnythingLLM's implementation.

### 6.4 Data Flow (Multi-Client Architecture)
```
FILE SYSTEM                                    ANYTHINGLLM INDEXING
    │                                               │
    ├─→ Wave Terminal creates/modifies file        │
    │       │                                       │
    │       ↓                                       │
    │   Sync Agent detects (watchfiles)            │
    │       │                                       │
    │       ├─→ Creates Workspace (if new)         │
    │       │                                       │
    │       └─→ Tells AnythingLLM: "Index this"    │
    │                               │               │
    │                               ↓               │
    │                   AnythingLLM Indexes         │
    │                   (creates vectors)           │
    │                           │                   │
    │                           ↓                   │
    └─────────────────→ AnythingLLM SQLite DB      │
                        (Documents + Embeddings)   │
                                 │
                    ┌────────────┬────────────┐
                    │            │            │
        ┌───────────↓──────────┐ │ ┌──────────↓────────────┐
        │  AnythingLLM UI      │ │ │  External Apps        │
        │  (localhost:3001)    │ │ │  (Wave, VSCode, etc.) │
        │                      │ │ │                       │
        │ Browsing + Query     │ │ │  API Calls:           │
        │                      │ │ │                       │
        │ → UI issues queries  │ │ │  1. POST /v1/rag/     │
        │   (model configured  │ │ │     search (8200)     │
        │    in AnythingLLM)   │ │ │                       │
        │                      │ │ │  2. POST /v1/chat/    │
        └──────────────────────┘ │ │     completions (8247)│
                                 │ │     (model of choice) │
                                 │ │                       │
                                 └─┴─────────────────────┘
```

---

## 7. Roadmap & Milestones

### Phase 1: Foundation (Current - Q1 2026)
- ✅ AnythingLLM Docker integration
- 🔄 CLI (`aitao.sh`) - start/stop/status/check
- 🔄 Sync Agent (`sync_agent.py`) - auto-create Workspaces from config
- 🔄 Basic RAG with AnythingLLM SQLite (text documents)
- 📋 **RAG Server API** (port 8200) - Generic document search for external apps
- 📋 **System Verification** (`check_system.py`) - Port + dependency checks

### Phase 2: Core Features (Q2 2026)
- 📋 Web search with opt-in consent
- 📋 Vision capabilities (Qwen-VL/Llava) for OCR and image analysis
- 📋 Enhanced file type support (audio, video metadata)
 - 📋 Setup-time UI choice (AnythingLLM Docker vs. Kotaemon Gradio vs. API-only) with clear trade-offs (Docker requirement/footprint vs. lightweight)

### Phase 3: Advanced Capabilities (Q3 2026)
- 📋 Image/SVG generation (open-source models)
- 📋 Audio/video transcription (Whisper alternative)
- 📋 External app integration API (Wave Terminal, etc.)

### Phase 4: Polish & Expansion (Q4 2026+)
- 📋 Linux and Windows support
- 📋 Zero-config installer (auto-install Python, Docker, models)
- 📋 Performance optimization
- 📋 Advanced security features (encryption, sandboxing)

**Agile Approach:** Iterate with mini functional victories, testable at each step. Decide dependencies collaboratively as we progress.

---

## 8. Dependencies & Integrations

### Current Stack (Decided)
- HuggingFace models (open-source)
- LanceDB (vector database)
- llama.cpp / llama-cpp-python (inference)
- AnythingLLM (UI framework, Docker)
- Python 3.14 + Bash

### Future Explorations (To Be Decided Collaboratively)
- Vision models (Qwen-VL, Llava, alternatives)
- Image generation models (Flux, Stable Diffusion, alternatives)
- Audio transcription (Whisper alternatives)
- Additional UI frontends
- External agent frameworks

**Decision Process:** Agile, iterative exploration of most relevant tools at each step.

---

## 9. Quality & Metrics

### Measurement Strategy
**V1 Approach:** Implement telemetry system to collect metrics and make data-driven decisions.

### Key Metrics (To Be Defined)
- **Performance:**
  - Query latency (time from question to answer)
  - Indexing speed (time to process X GB of documents)
  - Resource utilization (CPU/GPU/RAM %)
- **Quality:**
  - RAG relevance (user feedback on results)
  - OCR accuracy (% correct characters)
  - Search recall (% of expected documents found)
- **UX:**
  - User satisfaction scores
  - Error rate (% of failed queries)
  - Time to complete common tasks

---

## 10. Licensing & Commercialization

### Open Source Approach
- **Creator Attribution:** Philippe must be named as creator
- **Commercialization Rights:** Creator retains right to commercialize if successful
- **Community Contributions:** Welcome, with proper attribution
- **License Type:** TBD - Need guidance to balance:
  - Open-source collaboration
  - Commercial viability
  - Creator attribution
  - Derivative work permissions

**Action Item:** Research appropriate open-source licenses (MIT, Apache 2.0, GPL variants, or custom).

---

## 11. Out of Scope (V1 Non-Goals)

- ❌ Cloud integration or cloud-based processing
- ❌ User accounts or authentication systems
- ❌ Mobile apps (iOS/Android)
- ❌ Telemetry or data collection sent to external servers
- ❌ Built-in payment or subscription systems
- ❌ Multi-user collaboration features
- ❌ Real-time synchronization across devices

---

## 12. Success Criteria

### V1 Launch Success
AI Tao V1 is considered successful if:
1. A non-technical user can install and start using it within 15 minutes
2. Users can search 100GB+ of documents with relevant results in <5 seconds
3. OCR accurately extracts tables from scanned PDFs with >90% accuracy
4. System runs stably for 30+ days without crashes
5. Users report feeling "in control" of their data
6. Zero external data leakage (verified via network monitoring)

### Long-Term Success
- 10,000+ active users within 1 year
- Community contributors expanding capabilities
- Featured in privacy-focused tech publications
- Viable commercial offering for power users/enterprises
- Demonstrable environmental impact (carbon savings vs. cloud AI)

---

## 13. Open Questions & Risks

### Questions Requiring Resolution
1. **License:** Which open-source license best fits commercialization + attribution goals?
2. **Sandboxing:** Define security boundaries for processing untrusted files
3. **Audit Policies:** Clarify any compliance requirements (GDPR, local regulations)
4. **UX Metrics:** Establish baseline performance targets after user testing
5. **Whisper Alternative:** Which open-source transcription engine to adopt?

### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| **User hardware insufficient** | High | Clear minimum specs, model size recommendations |
| **AnythingLLM compatibility issues** | Medium | Maintain sync_agent flexibility, consider alternative UIs |
| **Model quality/performance** | Medium | Extensive testing, model selection guidance |
| **Complexity barrier** | High | Zero-config installer, comprehensive docs |
| **Licensing conflicts** | Low | Careful license review of all dependencies |

---

## 14. Appendix: Glossary

- **RAG (Retrieval-Augmented Generation):** AI technique combining vector search with generative models
- **LanceDB:** Modern vector database for AI applications
- **llama.cpp:** Efficient C++ inference engine for LLM models
- **AnythingLLM:** Open-source knowledge management and chat UI
- **Workspace:** AnythingLLM term for indexed document collections
- **Offline-first:** Architecture prioritizing local operation over network dependencies
- **Opt-in:** Feature requiring explicit user consent before activation

---

**Document Status:** Living document, updated iteratively as project evolves.  
**Next Review:** After Phase 1 completion (CLI + Sync Agent + Basic RAG).

---

*© 2026 AI Tao Project - Built for humans, powered by silicon.*
