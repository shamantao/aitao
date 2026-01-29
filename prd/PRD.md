# Product Requirements Document (PRD)
# AI Tao 2.0 - Local-First Search & Translation Engine

**Version:** 2.2.15  
**Date:** January 28, 2026  
**Status:** Active - Sprint 3 RAG/LLM starting  
**Author:** shamantao (AI Tao Project)  
**Branch:** `pdr/v2-remodular`

---

## Current Progress

| Sprint | Status | Version | Tests |
|--------|--------|---------|-------|
| Sprint 0: Foundation | ✅ Complete | v2.0.5 → v2.1.8 | 85 |
| Sprint 1: Indexation | ✅ Complete | v2.1.9 → v2.1.11 | 218 |
| Sprint 2: Recherche | ✅ Complete | v2.2.11 → v2.2.15 | 370 |
| Sprint 3: RAG & LLM | 🔄 Starting | v2.3.x | - |

### Completed Components
- ✅ PathManager, Logger, ConfigManager (Core)
- ✅ LanceDB Client (Vector Search, 26 tests)
- ✅ Meilisearch Client (Full-text, 25 tests)
- ✅ CLI Typer/Rich (9 tests)
- ✅ Filesystem Scanner + Queue + Worker (113 tests)
- ✅ TextExtractor + DocumentIndexer (69 tests)
- ✅ FastAPI + HybridSearch + Health (83 tests)

### Current: Sprint 3 - RAG & LLM Integration (Ollama)

---

## Executive Summary

**AItao** is a local-first, privacy-focused document search and translation engine that runs entirely on your personal computer. It empowers users to find, understand, and translate documents across their filesystem without sacrificing data privacy or paying cloud subscriptions.

**Core Principle:** *"Your data are your own. What happens on your Mac, stays on your Mac."*

**V2 Mission:** Build a modular, production-ready **document retrieval and translation system** with priority on:
- **Traditional Chinese → French/English** translation accuracy
- **Semantic search** across all personal documents (< 1TB, < 500K files)
- **Zero external dependencies** (no API keys, all free/open-source)
- **Modular architecture** (every component is replaceable)

---

## 1. Vision & Core Values

### Vision
Create a **privacy-first knowledge retrieval system** that empowers users to find, understand, and translate documents across their entire filesystem—without sacrificing privacy, speed, or control.

### Core Values
1. **🔒 Absolute Privacy**: Documents never leave the local machine
2. **🧩 Modularity**: Each component (indexer, search, OCR, translation, API) is independent and replaceable
3. **🔧 Maintainability**: Clean code, standard interfaces, comprehensive logging
4. **⚡️ Efficiency**: Optimized for limited resources (Mac M1, not cloud servers)
5. **💰 Zero Cost**: All models and tools are free and open-source (no API keys)
6. **🎯 Accuracy**: Translation and OCR quality prioritized over speed for critical documents
7. **🔄 Reversibility**: All decisions must be revertable—users can correct categorizations, swap models, change storage
8. **🔌 Interoperability**: AItao exposes standard APIs (Ollama/OpenAI-compatible) so any external tool can connect without code changes

---

## 2. Target User & Use Cases

### Primary Persona: "Multilingual Knowledge Worker"
- **Profile**: Professional managing mixed-language documents (Traditional Chinese, French, English)
- **Pain Points**:
  - Cannot read Chinese but receives important docs (government, business, school)
  - Forgets where files are stored (Dropbox, local drive, external HD, clouds)
  - Spotlight/Finder fails on semantic search ("where's the Germany trip doc from June 2025?")
  - Needs quick answers: "What are the deadlines in this accountant's doc?"
- **Success Criteria**: 
  - Find document in <5 seconds with natural language query
  - Get accurate translation + summary in <30 seconds
  - Never expose documents to external services

### Critical Use Cases (MVP)

#### UC-001: Semantic Document Search 🔥
**User Query:**
> "Where is the document about the Germany trip in June 2025?"

**System Response:**
1. Searches **Meilisearch** (full-text + filters) + **LanceDB** (semantic) in parallel
2. Returns: `/Dropbox/travel/germany_2025.pdf - This document mentions a trip to Germany from June 10-15, 2025...` (score: 0.95)
3. User clicks → file opens in default app

**Requirements:**
- Query latency: <3 seconds for 500K documents
- Hybrid search (full-text + semantic)
- Filters: date, path, category, file type

---

#### UC-002: Document Translation & Action Extraction 🔥
**User Request:**
> "The accountant sent me a Chinese document with tasks. What are the deadlines?"

**System Response:**
1. OCR if scanned (Qwen-VL for tables, AppleScript for simple text)
2. Translate Traditional Chinese → French/English
3. Extract structured data: deadlines, tasks, amounts
4. Returns:
   - Full translation
   - "Task 1: Invoice preparation - Due 2026-02-15 (15 days remaining)"
   - "Task 2: Tax filing - Due 2026-03-01 (32 days remaining)"

**Requirements:**
- Human-readable translation (context-aware, not word-for-word)
- Table structure preserved (JSON/CSV output)
- Entity extraction (dates, amounts, names)

---

#### UC-003: Filesystem Scanning & Auto-Indexing 🚀
**User Setup:**
> "Index all my Dropbox and external hard drives daily"

**System Behavior:**
1. **Daily cronjob** (2am) scans configured volumes
2. For each new/modified file:
   - Extract text (direct or OCR)
   - Extract EXIF metadata (images)
   - **Auto-categorize** (enterprise/school/sports/leisure/news)
   - Add to **JSON queue**
3. **Background worker** processes queue (throttle based on system load)
4. User gets summary: "15 new documents indexed, 3 need manual review"

**Requirements:**
- Watch filesystem changes (macOS FSEvents)
- Queue: JSON files in `~/Downloads/_sources/aitao/queue/`
- System load detection (pause if CPU >80%)

---

#### UC-004: Manual Document Ingestion (Priority) 🚀
**User Command:**
```bash
aitao ingest /path/to/document.pdf --ocr qwen-vl --priority high
```

**System Response:**
1. Skips queue (high priority)
2. Shows progress: "Processing... 30% done"
3. On completion:
   - Displays translation + extracted tables
   - Asks: "Categorize as [enterprise/school/other]?"
   - Indexes into LanceDB + Meilisearch

**Requirements:**
- Real-time progress feedback
- User can cancel/pause
- Priority queue (user > background)

---

#### UC-005: Category Correction 🔮
**User Action:**
> "This news magazine was classified as 'cooking' because of a recipe. Reclassify as 'news/international'"

**System Response:**
1. Updates document metadata
2. Saves correction to `corrections.json`
3. Future scans use learned patterns

**Requirements:**
- User-friendly category picker
- Feedback loop for model improvement

---

#### UC-006: RAG Integration (Continue/Wave/Custom UI) 🚀
**Architecture:**
AItao acts as a **RAG Hub** - external applications (AnythingLLM, Continue.dev, Open WebUI, etc.) connect to AItao instead of directly to Ollama. AItao enriches queries with relevant document context before forwarding to the LLM.

```
Client → AItao API (port 5000) → RAG Enrichment → Ollama (port 11434)
                                       ↓
                              LanceDB + Meilisearch
```

**Chat Request (Ollama-compatible):**
```json
POST /api/chat
{
  "model": "qwen2.5-coder:7b",
  "messages": [
    {"role": "user", "content": "Where is the Germany trip doc?"}
  ],
  "stream": true
}
```

**AItao Processing:**
1. Receive user prompt
2. Search RAG (LanceDB + Meilisearch) for relevant context
3. Enrich prompt with document snippets
4. Forward to Ollama
5. Store prompt + response in ChatHistory (indexed for future search)
6. Stream response back to client

**Search Request (unchanged):**
```json
POST /api/search
{
  "query": "Germany trip June 2025",
  "filters": {"date_after": "2025-01-01"},
  "limit": 5
}
```

**Requirements:**
- **Ollama-compatible API**: `/api/chat`, `/api/generate`, `/api/tags` (list models)
- **OpenAI-compatible API**: `/v1/chat/completions`, `/v1/models`
- AItao as transparent proxy (clients configure `http://localhost:5000` as their LLM endpoint)
- Shared RAG (LanceDB + Meilisearch) for all models
- ChatHistory indexed for future search ("What did I ask about Germany last week?")
- User file requests = **HIGH priority** in queue (vs auto-scan = NORMAL)

---

## 3. Functional Requirements

### FR-001: Modular Architecture ✅ CRITICAL

**Principle:** All components communicate via **standard interfaces** (REST API, JSON files, shared databases). Each module can be replaced without breaking others.

**Core Modules:**

#### 1. PathManager (`src/core/pathmanager.py`)
- Central registry of all file paths (code, config, logs, models, data)
- Returns absolute paths based on environment (dev/prod)
- **Never hard-code paths in source code**

#### 2. Logger (`src/core/logger.py`)
- Structured JSON logging
- Separate log files per module (indexer.log, ocr.log, api.log)
- Log rotation (100MB max per file)
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

#### 3. ConfigManager (`src/core/config.py`)
- Loads `config.yaml` (centralized config)
- Validates schema, provides defaults
- Hot-reload on file change

#### 4. ShellManager (`aitao.sh`)
- CLI entry point: `start`, `stop`, `status`, `ingest`, `search`
- Dashboard: Shows service status, queue length, resource usage

**Directory Structure:**
```
# Code (Git-tracked)
/Users/phil/Library/CloudStorage/Dropbox/devwww/AI-model/aitao/
├── src/
│   ├── core/              # PathManager, Logger, Config
│   ├── indexation/        # Scanner, queue, worker
│   ├── search/            # Meilisearch + LanceDB integration
│   ├── ocr/               # OCR router, Qwen-VL, AppleScript
│   ├── translation/       # Translation pipeline
│   ├── api/               # FastAPI REST endpoints
│   └── dashboard/         # CLI/TUI dashboard
├── config/
│   ├── config.yaml        # Main config
│   └── categories.yaml    # Category definitions
├── scripts/               # One-shot scripts (benchmarks, migrations)
├── tests/
└── aitao.sh               # CLI entry point

# Data/Logs/Models (Not Git-tracked, local only)
/Users/phil/Downloads/_sources/aitao/
├── models/                # GGUF files, mmproj
├── logs/                  # JSON logs
├── lancedb/               # Vector index
├── meilisearch/           # Full-text index (if not using host)
├── cache/                 # OCR cache, translation cache
├── queue/                 # JSON task queue
└── corrections/           # User feedback (corrections.json)

# Test data (dev)
/Users/phil/Downloads/_Volumes/
└── [scanned PDFs, images, docs]

# Production (configured in config.yaml)
[Various clouds/external drives]
```

---

### FR-002: Configuration Management 🔄

**Single config file:** `config.yaml`

**Schema:**
```yaml
version: "2.0"

# Paths
paths:
  storage_root: "/Users/phil/Downloads/_sources/aitao"
  models_dir: "${storage_root}/models"
  logs_dir: "${storage_root}/logs"
  test_volumes: ["/Users/phil/Downloads/_Volumes"]
  prod_volumes: []  # Add production cloud paths here

# Indexing
indexing:
  scan_interval: "daily"  # cron: 0 2 * * * (2am daily)
  watch_filesystem: true
  supported_extensions:
    text: [".txt", ".md", ".json", ".toml", ".yaml", ".conf"]
    documents: [".pdf", ".docx", ".odt", ".pptx", ".odp", ".xlsx"]
    images: [".jpg", ".png", ".webp"]
    code: [".py", ".js", ".ts", ".cpp", ".java"]
  skip_patterns: [".*", "__pycache__", "node_modules", ".git"]
  auto_categorize: true
  extract_exif: true  # For images

# OCR
ocr:
  default_engine: "applescript"  # Fast for simple text
  fallback_engine: "qwen-vl"     # Tables, complex layouts
  router:
    table_detection_threshold: 0.7
    use_qwen_for_tables: true
  qwen_vl:
    model_path: "${models_dir}/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
    mmproj_path: "${models_dir}/Qwen2.5-VL-7B-Instruct-mmproj-bf16.gguf"
    max_tokens: 4096
    temperature: 0.1  # Deterministic
    table_output_format: "json"  # json, csv, markdown

# Translation
translation:
  source_languages: ["zh-TW"]  # Traditional Chinese
  target_languages: ["fr", "en"]
  model: "qwen2.5-coder-7b-instruct"  # Or dedicated translation model
  cache_enabled: true

# Search
search:
  meilisearch:
    host: "http://localhost:7700"  # Use host instance
    api_key: null  # If required
    index_name: "aitao_documents"
  lancedb:
    path: "${storage_root}/lancedb"
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  hybrid_search:
    meilisearch_weight: 0.4
    lancedb_weight: 0.6

# Categories
categories:
  predefined: ["enterprise", "school", "sports", "leisure", "news", "personal"]
  allow_custom: true

# API
api:
  host: "127.0.0.1"
  port: 5000
  cors_origins: ["http://localhost:3000"]  # Custom UI

# Resources
resources:
  max_cpu_percent: 80  # Throttle if system > 80% CPU
  max_memory_gb: 8
  gpu_enabled: true  # Apple Metal

# Logging
logging:
  level: "INFO"
  format: "json"
  max_size_mb: 100
```

---

### FR-003: Search Engine (Hybrid) 🔄

**Components:**
1. **Meilisearch** (host instance at `localhost:7700`)
   - Full-text search with typo tolerance
   - Fast filtering (date, path, category)
   - Faceted search

2. **LanceDB** (local vector DB)
   - Semantic embeddings (all-MiniLM-L6-v2)
   - Similarity search
   - Metadata storage (file path, hash, OCR method, language)

**Search Workflow:**
```
User query → API
  ├─→ Meilisearch (full-text + filters) [parallel]
  └─→ LanceDB (semantic vectors)        [parallel]
       ↓
  Merge results (weighted ranking: 40% Meilisearch, 60% LanceDB)
       ↓
  Return top 10 with summaries
```

**API Endpoint:**
```python
POST /api/search
{
  "query": "Germany trip June 2025",
  "filters": {
    "date_after": "2025-01-01",
    "path_contains": "Dropbox",
    "category": "personal"
  },
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "sha256:abc123...",
      "path": "/Users/phil/Dropbox/travel/germany_2025.pdf",
      "title": "Germany Trip Itinerary",
      "summary": "Trip to Germany from June 10-15, 2025...",
      "score": 0.95,
      "metadata": {
        "date_modified": "2025-06-01T10:30:00Z",
        "category": "personal",
        "language": "en",
        "ocr_method": "direct"
      }
    }
  ],
  "query_time_ms": 234
}
```

---

### FR-004: OCR Pipeline 🔄

**OCR Router Logic:**
```python
def route_ocr(file_path):
    # 1. Try direct text extraction (pdfminer, pypdf)
    text = extract_text_direct(file_path)
    if is_sufficient(text):
        return {"method": "direct", "text": text}
    
    # 2. Detect tables (OpenCV contours)
    has_tables = detect_tables(file_path, threshold=0.7)
    
    if has_tables:
        # Use Qwen-VL for table extraction
        return qwen_vl_ocr(file_path, extract_tables=True)
    else:
        # Use AppleScript OCR (fast, macOS native)
        return applescript_ocr(file_path)
```

**Qwen-VL Configuration:**
```yaml
qwen_vl:
  model_path: "${models_dir}/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
  mmproj_path: "${models_dir}/Qwen2.5-VL-7B-Instruct-mmproj-bf16.gguf"
  max_tokens: 4096
  temperature: 0.1  # Deterministic for OCR
  table_extraction:
    output_format: "json"  # Also supports csv, markdown
    preserve_structure: true
```

**Output Cache:**
- OCR results cached in `${storage_root}/cache/ocr/`
- Filename: `{file_sha256}.json`
- Content:
  ```json
  {
    "file_path": "/path/to/doc.pdf",
    "sha256": "abc123...",
    "ocr_method": "qwen-vl",
    "timestamp": "2026-01-28T10:30:00Z",
    "text": "...",
    "tables": [
      {
        "table_id": 1,
        "data": [[...], [...]]
      }
    ]
  }
  ```

---

### FR-005: Translation Pipeline 📋

**Workflow:**
```
Chinese document → OCR → Translation LLM → French/English
                                        ↓
                             Extract actions/deadlines
                                        ↓
                             Save to cache + index
```

**Translation Prompt Template:**
```
You are a professional translator specializing in Traditional Chinese (Taiwan) to French/English.

Document excerpt:
"""
{chinese_text}
"""

Tasks:
1. Translate to French (formal, context-aware)
2. Identify:
   - Deadlines (dates, timeframes)
   - Action items (tasks, requirements)
   - Key entities (names, amounts, organizations)

Output format (JSON):
{
  "translation_fr": "...",
  "translation_en": "...",
  "deadlines": [
    {
      "task": "Invoice preparation",
      "date": "2026-02-15",
      "days_remaining": 15
    }
  ],
  "actions": ["Submit form", "Gather documents"],
  "entities": {
    "names": ["Chen Wei", "Taipei Office"],
    "amounts": ["NT$50,000"],
    "organizations": ["Ministry of Finance"]
  }
}
```

**Cache:**
- Translations cached in `${storage_root}/cache/translations/`
- User can view original + translation side-by-side in UI

---

### FR-006: Indexing & Queue System 🔄

**Components:**

#### 1. Filesystem Scanner (`src/indexation/scanner.py`)
- Scans volumes daily (cronjob: `0 2 * * *`)
- Watches filesystem changes (macOS FSEvents)
- Detects new/modified files (compare mtime + SHA256)
- Adds to queue

#### 2. Task Queue (`${storage_root}/queue/tasks.json`)
- JSON array of tasks:
  ```json
  [
    {
      "id": "uuid-1234",
      "file_path": "/path/to/doc.pdf",
      "task_type": "ocr",
      "priority": "normal",
      "added_at": "2026-01-28T10:00:00Z",
      "status": "pending"
    }
  ]
  ```
- Priority levels: `high` (user request), `normal` (auto scan), `low` (re-indexing)

#### 3. Background Worker (`src/indexation/worker.py`)
- Polls queue every 30 seconds
- Processes tasks sequentially (respects system load)
- Updates task status: `pending` → `processing` → `completed` / `failed`

#### 4. System Load Monitor
- Checks CPU/Memory usage before processing
- If system busy (>80% CPU), pauses worker
- Detects user activity (mouse/keyboard events) → deprioritize background tasks

**Workflow:**
```
Scanner → Queue → Worker → OCR/Translation → Index (LanceDB + Meilisearch)
                     ↓
              Log + Notify user
```

---

### FR-007: Category Management 📋

**Predefined Categories:** (in `config/categories.yaml`)
```yaml
categories:
  - id: "enterprise"
    label_fr: "Entreprise"
    label_en: "Business"
    keywords_fr: ["contrat", "facture", "comptabilité"]
    keywords_en: ["contract", "invoice", "accounting"]
    keywords_zh: ["合約", "發票", "會計"]
  
  - id: "school"
    label_fr: "Scolarité"
    label_en: "Education"
    keywords_fr: ["école", "bulletin", "cours"]
    keywords_en: ["school", "report", "class"]
    keywords_zh: ["學校", "成績單", "課程"]
  
  - id: "sports"
    label_fr: "Sport"
    label_en: "Sports"
    keywords_fr: ["entraînement", "match", "club"]
    keywords_en: ["training", "match", "club"]
    keywords_zh: ["訓練", "比賽", "俱樂部"]
  
  - id: "leisure"
    label_fr: "Loisirs"
    label_en: "Leisure"
    keywords_fr: ["voyage", "restaurant", "cinéma"]
    keywords_en: ["travel", "restaurant", "cinema"]
    keywords_zh: ["旅行", "餐廳", "電影"]
  
  - id: "news"
    label_fr: "Actualités"
    label_en: "News"
    keywords_fr: ["journal", "magazine", "info"]
    keywords_en: ["newspaper", "magazine", "news"]
    keywords_zh: ["報紙", "雜誌", "新聞"]
```

**Auto-Categorization:**
- LLM analyzes document title + first 1000 words + keywords
- Returns category + confidence score
- If confidence < 0.7 → flag for manual review

**Corrections:**
- Stored in `${storage_root}/corrections/corrections.json`
- Format:
  ```json
  {
    "corrections": [
      {
        "file_sha256": "abc123",
        "old_category": "leisure",
        "new_category": "news",
        "reason": "Magazine with recipe, but mainly news",
        "corrected_at": "2026-01-28T10:00:00Z"
      }
    ]
  }
  ```
- Future: Use corrections to fine-tune categorization model

---

### FR-008: API & External Integration 🔄

**FastAPI REST Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Hybrid search (Meilisearch + LanceDB) |
| `/api/ingest` | POST | Manual file ingestion (priority: HIGH) |
| `/api/translate` | POST | Translate document on-demand |
| `/api/categories` | GET | List categories |
| `/api/categories/{id}` | PUT | Update category for document |
| `/api/queue` | GET | View task queue status |
| `/api/health` | GET | Service health check |
| `/api/stats` | GET | Indexing stats (total docs, by category, by language) |

**LLM/Chat Endpoints (Ollama-compatible):**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with RAG context (streaming SSE) |
| `/api/generate` | POST | Text generation (non-chat) |
| `/api/tags` | GET | List available models (from Ollama) |
| `/api/embeddings` | POST | Generate embeddings |

**LLM/Chat Endpoints (OpenAI-compatible):**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | OpenAI-compatible chat |
| `/v1/models` | GET | List available models |
| `/v1/embeddings` | POST | Generate embeddings |

**Shared RAG Access:**
- Any LLM client can connect to AItao (port 5000) instead of Ollama directly
- AItao enriches prompts with RAG context before forwarding to Ollama
- LanceDB/Meilisearch shared (no data duplication)
- ChatHistory stored and indexed for future search
- JWT auth for security (optional, V2+)

**OpenAPI Schema:**
- Auto-generated documentation at `/docs`
- Client SDKs can be generated for external apps

---

### FR-009: CLI & Dashboard 🔄

**CLI Commands:**
```bash
./aitao.sh start            # Start all services (API, worker, cronjob)
./aitao.sh stop             # Stop services
./aitao.sh status           # Show status dashboard
./aitao.sh ingest <path>    # Ingest file/folder
./aitao.sh search "query"   # CLI search
./aitao.sh logs <module>    # View logs (indexer, ocr, api)
./aitao.sh config edit      # Open config.yaml in editor
./aitao.sh config validate  # Validate config schema
```

**Dashboard (TUI):**
```
┌─ AItao Status ────────────────────────────────────────┐
│ API:         ● Running (port 5000)                    │
│ Worker:      ● Processing (2 tasks in queue)          │
│ Meilisearch: ● Connected (localhost:7700)             │
│ LanceDB:     ● Ready (125K documents)                 │
├───────────────────────────────────────────────────────┤
│ Resources:                                            │
│   CPU:  45% ████████░░░░░░░░                         │
│   RAM:  6.2 / 16 GB                                   │
│   Disk: 87 / 500 GB                                   │
├───────────────────────────────────────────────────────┤
│ Recent Activity:                                      │
│   [10:30] Indexed: /Dropbox/invoices/2025.pdf        │
│   [10:28] OCR completed: document_scan.jpg            │
│   [10:25] Search query: "Germany trip"                │
└───────────────────────────────────────────────────────┘
```

---

### FR-010: LLM Backend & Interoperability 🚀 NEW

**Architecture Principle:**
AItao uses **Ollama** as the LLM backend to ensure maximum interoperability with third-party applications. Ollama is the de-facto standard for local LLM serving, supported by AnythingLLM, Continue.dev, Open WebUI, LangChain, and many others.

**Why Ollama (not llama.cpp server):**

| Feature | llama.cpp server | Ollama |
|---------|------------------|--------|
| Multi-model support | ❌ 1 per instance | ✅ Native |
| Hot-swap models | ❌ Restart required | ✅ On-the-fly |
| Model discovery API | ❌ No `/api/tags` | ✅ Full support |
| Third-party app support | ⚠️ Limited | ✅ Universal |
| Installation | ⚠️ Manual compile | ✅ `brew install ollama` |
| Memory management | ⚠️ Manual | ✅ Automatic |

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                        External Clients                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ AnythingLLM  │  │ Continue.dev │  │  Open WebUI  │  CLI Chat     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │        │
│         │                 │                 │               │        │
│         └─────────────────┴─────────────────┴───────────────┘        │
│                                   │                                  │
│                    Configure: http://localhost:5000                  │
│                    (NOT http://localhost:11434)                      │
│                                   │                                  │
│                                   ▼                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    AItao API (Port 5000)                       │  │
│  │                    ══════════════════════                       │  │
│  │  Endpoints (Ollama-compatible):                                │  │
│  │    /api/chat, /api/generate, /api/tags, /api/embeddings        │  │
│  │  Endpoints (OpenAI-compatible):                                 │  │
│  │    /v1/chat/completions, /v1/models, /v1/embeddings            │  │
│  │                                                                 │  │
│  │  RAG Pipeline:                                                  │  │
│  │    1. Receive prompt                                            │  │
│  │    2. Search context (LanceDB + Meilisearch)                   │  │
│  │    3. Enrich prompt with relevant documents                    │  │
│  │    4. Forward to Ollama                                         │  │
│  │    5. Store prompt+response in ChatHistory                     │  │
│  │    6. Stream response to client                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                   │                                  │
│                                   ▼                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Ollama (Port 11434)                         │  │
│  │  Models: qwen2.5-coder:7b, llama3.1:8b, qwen2-vl:7b           │  │
│  │  (managed via `ollama pull` or `ollama create`)                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    AItao Storage                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│  │  │  LanceDB    │  │ Meilisearch │  │ ChatHistory │             │  │
│  │  │  (vectors)  │  │ (full-text) │  │ (indexed)   │             │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Configuration (`config.yaml`):**
```yaml
llm:
  backend: "ollama"                    # ollama (recommended) or llamacpp
  ollama:
    host: "http://localhost:11434"     # Ollama server
    default_model: "qwen2.5-coder:7b"  # Default for chat
    models:                            # Models to ensure are available
      - "qwen2.5-coder:7b"
      - "llama3.1:8b"
      - "qwen2-vl:7b"
  rag:
    enabled: true
    max_context_docs: 5                # Max documents to include in context
    context_max_tokens: 2000           # Max tokens for RAG context
    system_prompt: "config/system_prompt.txt"
  chat_history:
    enabled: true
    index_conversations: true          # Index prompts/responses for search
    retention_days: 365                # Keep history for 1 year
```

**Service Management:**
```bash
./aitao.sh start    # Starts: Ollama (if not running) + API + Worker
./aitao.sh stop     # Stops: API + Worker (Ollama continues for other apps)
./aitao.sh status   # Shows: Ollama status, models loaded, AItao services
```

**Key Behaviors:**
1. **Transparent Proxy**: Clients configure AItao as their "Ollama endpoint" - they don't know the difference
2. **RAG Enrichment**: Every chat request is enriched with relevant document context
3. **ChatHistory Indexing**: All prompts and responses are stored and indexed for future search
4. **Priority Ingestion**: Files requested by user during chat = HIGH priority in queue
5. **Multi-Model**: Ollama manages model loading/unloading automatically

---

## 4. Non-Functional Requirements

### NFR-001: Platform Support
- **V1 Priority:** macOS (Apple Silicon M1+)
- **Future:** Linux, Windows (Intel/AMD)
- **Python:** 3.13+ (managed via `uv`)
- **GPU:** Apple Metal (macOS), CUDA (Linux/Windows future)

### NFR-002: Performance
- **Search latency:** <3 seconds for 500K documents
- **OCR latency:** 
  - AppleScript: <10 seconds for simple PDF
  - Qwen-VL: 10-15 minutes for complex scanned document with tables (acceptable for accuracy)
- **Translation latency:** <30 seconds for 1-page document
- **Resource throttling:** Pause background tasks if CPU >80% or user active

### NFR-003: Storage
- **Default Limit:** 500GB
- **Alerts:** Notify at 125GB, 250GB, 375GB, 500GB
- **Configurable:** Via `config.yaml`
- **Retention:** Oldest/least-used data purged when approaching limit

### NFR-004: Security & Privacy
- **Data locality:** 100% local, never uploaded
- **Logs:** Local storage only
- **Encryption:** Not implemented in V1 (future)
- **Access control:** Optional JWT auth for API (V2+)

### NFR-005: Maintainability
- **Modular code:** Each module <400 lines (refactor if larger)
- **File headers:** Every file starts with comment block explaining purpose
- **Logging:** Comprehensive JSON logs for debugging
- **Error handling:** Graceful degradation, clear error messages
- **Testing:** Unit tests for core modules, integration tests for pipelines

### NFR-006: Dependency Management
- **uv-first:** All Python dependencies managed via `uv` (not raw `pip`)
- **No hard-coded paths:** All paths via PathManager + config.yaml
- **Centralized logging:** All modules use shared Logger
- **Open-source only:** No proprietary dependencies

### NFR-007: LLM Interoperability 📌 NEW
- **Ollama as LLM backend:** Standard API for maximum compatibility
- **API Compatibility:** Expose both Ollama-compatible and OpenAI-compatible endpoints
- **Zero-code integration:** Third-party apps (AnythingLLM, Continue.dev, Open WebUI) connect via `config.yaml` only
- **Model discovery:** `/api/tags` and `/v1/models` endpoints list all available models
- **Transparent proxy:** Clients don't need to know about RAG enrichment

---

## 5. Technology Stack

### Core
- **Language:** Python 3.13+
- **Dependency Manager:** `uv` (Astral)
- **LLM Backend:** Ollama (multi-model, OpenAI-compatible API)
- **Vector DB:** LanceDB
- **Full-text Search:** Meilisearch (host instance)
- **API Framework:** FastAPI
- **Config:** YAML (`config.yaml`)

### Models (via Ollama)
- **LLM:** `qwen2.5-coder:7b` (code/translation), `llama3.1:8b` (general)
- **Vision:** `qwen2-vl:7b` (OCR, table extraction)
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (local, not via Ollama)

### GGUF Models (legacy, for direct llama-cpp use)
- Located in `_sources/AI-models/`
- Can be imported to Ollama via `ollama create`

### Tools
- **OCR:** AppleScript (macOS native), Qwen-VL (complex)
- **PDF:** pdfminer.six, pypdf
- **Image:** OpenCV (table detection), Pillow
- **EXIF:** piexif, exifread
- **CLI:** Bash (orchestration), Rich (TUI dashboard)

---

## 6. Development Phases

### Phase 1: Foundation (Jan 2026) ✅ Complete
- ✅ Directory structure
- ✅ Config.yaml schema
- ✅ PathManager, Logger, ConfigManager
- ✅ CLI (`aitao.sh`) - start/stop/status
- ✅ Meilisearch integration
- ✅ LanceDB integration

### Phase 2: Indexation & Search (Jan 2026) ✅ Complete
- ✅ Filesystem scanner + queue system
- ✅ Background worker
- ✅ Direct text indexing (txt, md, docx, pdf)
- ✅ Hybrid search (Meilisearch + LanceDB)
- ✅ FastAPI REST endpoints
- ✅ Health endpoint

### Phase 3: RAG & LLM (Feb 2026) 🔄 Current
- 📋 Ollama integration (OllamaClient)
- 📋 RAG Engine (search + enrich prompt)
- 📋 Chat endpoint `/api/chat` (Ollama-compatible)
- 📋 OpenAI-compatible endpoints (`/v1/chat/completions`)
- 📋 ChatHistory storage + indexing
- 📋 CLI chat command
- 📋 Continue.dev / AnythingLLM configuration guide

### Phase 4: OCR (Mar-Apr 2026) 📋
- 📋 OCR router (detect tables)
- 📋 AppleScript OCR integration
- ✅ Qwen-VL OCR (already tested)
- 📋 Table extraction (JSON output)
- 📋 OCR cache system

### Phase 5: Translation (Apr-May 2026) 📋
- 📋 Translation pipeline (zh-TW → fr/en)
- 📋 Action extraction (deadlines, entities)
- 📋 Translation cache
- 📋 Prompt engineering for accuracy

### Phase 6: Categorization (May-Jun 2026) 📋
- 📋 Auto-categorization (LLM-based)
- 📋 Category correction UI/API
- 📋 Feedback loop (corrections.json)

### Phase 7: Polish (Jun-Jul 2026) 🔮
- 📋 Dashboard (TUI)
- 📋 EXIF extraction (images)
- 📋 System load monitoring
- 📋 Comprehensive testing
- 📋 Documentation

---

## 7. Success Metrics

### User Experience
- **Search accuracy:** >90% relevant results in top 5
- **Translation quality:** Human-readable, context-aware (manual evaluation)
- **Query latency:** <3 seconds
- **User satisfaction:** "I found what I needed" >80%

### Technical
- **Indexing throughput:** 100 documents/hour (simple text), 10 documents/hour (OCR)
- **System resource usage:** <80% CPU during background tasks
- **Error rate:** <1% failed indexing tasks
- **Cache hit rate:** >70% for repeated queries/documents

### Business
- **Zero cost:** No API subscriptions, all free/open-source
- **Privacy:** 100% local processing
- **Modularity:** Each component replaceable within 1 day of dev work

---

## 8. Known Limitations & Future Work

### MVP Limitations
- **No email support:** Gmail/Outlook indexing not included
- **macOS only:** Linux/Windows support deferred
- **No encryption:** Documents stored in plaintext
- **No collaborative features:** Single-user system
- **No web search:** Removed from V2 scope (focus on local docs)

### V2 Scope (Interoperability) ✅ NEW
- ✅ **Universal LLM API:** Ollama-compatible + OpenAI-compatible endpoints
- ✅ **Zero-code integration:** Third-party apps connect via config only
- ✅ **RAG Hub:** AItao enriches all LLM queries with document context
- ✅ **ChatHistory indexing:** Search past conversations

### Future Enhancements (V3+)
- **Fine-tuning:** Use corrections to improve categorization model
- **Audio/Video:** Transcription support
- **Image generation:** Local image generation models
- **Multi-platform:** Linux, Windows support
- **Email indexing:** IMAP/MBOX integration
- **Encryption:** At-rest encryption for sensitive docs

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Qwen-VL too slow for large volumes | High | Medium | Prioritize AppleScript OCR, use Qwen-VL only for tables |
| Translation quality insufficient | High | Medium | Benchmark multiple models, allow user to swap models |
| System resource overload | Medium | High | Implement load monitoring, queue throttling |
| Category errors (misclassification) | Low | High | Manual correction UI, feedback loop |
| Filesystem changes not detected | Medium | Low | Use robust FSEvents, fallback to periodic scans |

---

## 10. Open Questions

1. **Meilisearch vs Standalone:** Use host instance or bundle Meilisearch Docker?  
   **Decision:** Benchmark both, prefer host for simplicity.

2. **Queue System:** JSON files or Redis/Celery?  
   **Decision:** JSON files (simpler, no external dependencies).

3. **Cronjob vs Daemon:** Daily cronjob or 24/7 daemon for filesystem watching?  
   **Decision:** Hybrid (cronjob for daily full scan, daemon for real-time changes).

4. **Translation Model:** Qwen-Coder or dedicated translation model?  
   **Decision:** Benchmark both, pick best accuracy.

5. **Table Format:** JSON, CSV, or both?  
   **Decision:** JSON (structured), with CSV export option.

---

## Appendix A: Configuration Example

See [FR-002](#fr-002-configuration-management-) for full `config.yaml` schema.

---

## Appendix B: API Documentation

OpenAPI schema available at `http://localhost:5000/docs` when API running.

---

## Appendix C: Logging Schema

All logs in JSON format:
```json
{
  "timestamp": "2026-01-28T10:30:00.123Z",
  "level": "INFO",
  "module": "indexer",
  "message": "Indexed document successfully",
  "metadata": {
    "file_path": "/path/to/doc.pdf",
    "sha256": "abc123...",
    "duration_ms": 1234
  }
}
```

---

**End of PRD v2.0**
