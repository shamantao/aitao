# Product Requirements Document (PRD)
# AI Tao - Local, Sovereign & Accessible AI Assistant

**Version:** 1.0  
**Date:** January 22, 2026  
**Status:** Draft  
**Author:** Philippe (AI Tao Project)

---

## Executive Summary

**AI Tao** is a local-first, privacy-focused AI assistant that runs entirely on your personal computer. It empowers users to leverage powerful AI capabilities without sacrificing data privacy, environmental sustainability, or paying expensive cloud subscriptions. AI Tao is the ultimate alternative to cloud-based AI services for users who want to own their data and their intelligence.

**Core Principle:** *"Your data are your own. What happens on your Mac, stays on your Mac."*

---

## 1. Vision & Mission

### Vision
Create an accessible, open-source AI assistant that preserves user privacy, reduces environmental impact, and democratizes AI technology for everyone with a capable personal computer.

### Mission
Deliver a production-ready tool that helps users with daily tasks—document search, translation, visual analysis, content generation—while keeping all data local and secure.

### Core Values
1. **🔒 Absolute Privacy**: Financial documents, contracts, and code never leave the hard drive
2. **⚡️ Radical Simplicity**: Users should not need to "code" to "use"—drop a file, ask a question
3. **🏗 Modularity**: Connect best-in-class open-source tools (llama.cpp, AnythingLLM, Python scripts) into a fluid ecosystem
   - **AI Tao must remain independent of any single UI or inference engine**
   - Users can swap tools without losing data or functionality
4. **🌱 Environmental Responsibility**: Local processing over cloud reduces carbon footprint
5. **💰 Zero Cost**: Free and open-source—users are not the product
6. **🔧 Developer Freedom**: External apps (Wave Terminal, VSCode, custom scripts) can access AI Tao's capabilities without depending on AnythingLLM's choices

---

## 2. Target Audience & Personas

### Primary Target
**General Public** with personal computers powerful enough to run AI models locally.

### User Personas

#### Persona 1: "Privacy-Conscious Professional"
- **Profile**: Lawyer, accountant, consultant handling sensitive documents
- **Needs**: Confidential document search, translation, analysis without cloud exposure
- **Technical Level**: Non-technical, expects "just works" experience

#### Persona 2: "Cost-Conscious Knowledge Worker"
- **Profile**: Student, freelancer, small business owner
- **Needs**: Cannot afford expensive AI subscriptions ($20-50/month)
- **Technical Level**: Basic computer skills, can follow simple instructions

#### Persona 3: "Developer/Power User"
- **Profile**: Software engineer wanting local AI for coding assistance
- **Needs**: Integration with terminal apps (Wave Terminal), code generation, local model control
- **Technical Level**: Advanced, comfortable with CLI and configuration files

#### Persona 4: "Digital Packrat"
- **Profile**: Anyone with years of accumulated files and forgotten documents
- **Needs**: Powerful search beyond Spotlight—semantic understanding of "where is that invoice from 2023?"
- **Technical Level**: Variable, needs intuitive interface

---

## 3. Use Cases (V1 Priority)

### UC-001: Local Document Search (Semantic)
**Priority:** 🔥 Critical  
**User Story (Variant A):** "I'm looking for a document about 'computer usage policy at Sesame Motor'"  
**User Story (Variant B):** "I forgot where I placed the roof work estimate, and forgot the company name"  
**Expected Behavior:**
- AI searches indexed volumes using semantic understanding
- **Variant A** (precise query): Returns "I found this document, located at [path], here's a summary..."
- **Variant B** (fuzzy recovery): Returns "You have several estimates about the house, located here. There's one standalone file from [company name]"
- Shows relevant excerpts with source citations
- **Key Feature**: More powerful than Spotlight—understands intent, not just keywords

### UC-002: Visual Analysis (OCR)
**Priority:** 🔥 Critical  
**User Story:** "I received an image via messaging but don't understand it, analyze it for me"  
**Expected Behavior:**
- AI analyzes image using vision model (Qwen-VL/Llava)
- Returns: "Here's what I see, and here's the translation/explanation..."
- Extracts tables from scanned PDFs → Excel/CSV

### UC-003: Web Search with Consent (Opt-in)
**Priority:** 🚀 High  
**User Story:** "I'm looking for the recipe for 'gloubiboulga'" [user checks web search option]  
**Expected Behavior:**
- AI explicitly asks: "This requires web search, proceed?"
- Performs secure, non-logged search via **DuckDuckGo** (privacy-respecting)
- Returns: "Here's the recipe from [source]" (Perplexity-style citations)
- Asks: "Do you want me to remember this recipe?" → indexes if yes, forgets if no

### UC-004: Image/SVG Generation
**Priority:** 🔮 Future  
**User Story:** "Create an image to illustrate my post about this topic"  
**Expected Behavior:**
- AI generates SVG or open-format image
- Returns: "Here's the image I propose in SVG format"

### UC-005: External Integration (Wave Terminal)
**Priority:** 🚀 High  
**User Story:** Developer wants to query AI from terminal/external app  
**Expected Behavior:**
- AI Tao exposes OpenAI-compatible API endpoint
- Wave Terminal (or other apps) can send prompts and receive responses

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
