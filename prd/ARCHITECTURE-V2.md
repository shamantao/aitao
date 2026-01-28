# AItao V2.0 - Architecture Technique

**Date:** January 28, 2026  
**Branch:** `pdr/v2-remodular`  
**Auteur:** shamantao

---

## 1. Vue d'ensemble

AItao V2 est une **architecture modulaire en couches** conçue pour la maintenabilité, l'extensibilité et la performance sur macOS (Apple Silicon M1+).

### Principes architecturaux

1. **Modularité**: Chaque composant est indépendant et remplaçable
2. **Interfaces standardisées**: Communication via API REST, JSON files, shared databases
3. **Découplage**: Pas de dépendances directes entre modules métier
4. **Observabilité**: Logging structuré (JSON), monitoring système
5. **Configuration centralisée**: Un seul fichier `config.yaml`
6. **Chemins managés**: PathManager pour tous les accès filesystem
7. **Ressources limitées**: Throttling basé sur charge système

---

## 2. Architecture en couches

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ CLI      │  │ REST API │  │ Continue │  │ Wave     │   │
│  │ (aitao.sh│  │ (FastAPI)│  │ (VSCode) │  │ Terminal │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
┌───────┼─────────────┼─────────────┼─────────────┼──────────┐
│       │          API GATEWAY (Port 5000)        │          │
│       └─────────────┬─────────────┬─────────────┘          │
│                     │             │                        │
│              ┌──────▼─────┐  ┌───▼────┐                   │
│              │ Search     │  │ Ingest │                   │
│              │ Service    │  │ Service│                   │
│              └──────┬─────┘  └───┬────┘                   │
└─────────────────────┼────────────┼────────────────────────┘
                      │            │
┌─────────────────────┼────────────┼────────────────────────┐
│              BUSINESS LOGIC LAYER                         │
│  ┌───────────▼────────┐   ┌──────▼──────┐                │
│  │ SearchEngine       │   │ Indexer     │                │
│  │ (Hybrid)           │   │ (Orchestr.) │                │
│  │ - Meilisearch      │   │ - Scanner   │                │
│  │ - LanceDB          │   │ - Queue     │                │
│  │ - Ranking          │   │ - Worker    │                │
│  └──────┬─────────────┘   └──────┬──────┘                │
│         │                        │                        │
│  ┌──────▼────────┐        ┌──────▼──────┐                │
│  │ OCR Pipeline  │        │ Translation │                │
│  │ - Router      │        │ - Translator│                │
│  │ - AppleScript │        │ - Actions   │                │
│  │ - Qwen-VL     │        │ Extractor   │                │
│  └───────────────┘        └─────────────┘                │
└───────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┼─────────────────────────────────────┐
│                DATA LAYER                                 │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐            │
│  │ LanceDB    │  │ Meilisearch│  │ JSON     │            │
│  │ (Vectors)  │  │ (Full-text)│  │ (Queue,  │            │
│  │            │  │            │  │  Cache)  │            │
│  └────────────┘  └────────────┘  └──────────┘            │
└───────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┼─────────────────────────────────────┐
│             INFRASTRUCTURE LAYER                          │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐            │
│  │ PathManager│  │ Logger     │  │ Config   │            │
│  │            │  │ (JSON)     │  │ Manager  │            │
│  └────────────┘  └────────────┘  └──────────┘            │
│  ┌────────────┐  ┌────────────┐                          │
│  │ System     │  │ LLM        │                          │
│  │ Monitor    │  │ Client     │                          │
│  └────────────┘  └────────────┘                          │
└───────────────────────────────────────────────────────────┘
```

---

## 3. Structure des répertoires

### 3.1 Code source (Git-tracked)

```
/Users/phil/Library/CloudStorage/Dropbox/devwww/AI-model/aitao/
├── aitao.sh                    # CLI entry point
├── pyproject.toml              # uv project config
├── requirements.txt            # Python dependencies
├── README.md
│
├── config/
│   ├── config.yaml             # Main configuration
│   ├── config.yaml.template    # Template for new installs
│   └── categories.yaml         # Category definitions
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                   # Infrastructure
│   │   ├── __init__.py
│   │   ├── pathmanager.py      # Centralized path management
│   │   ├── logger.py           # Structured JSON logging
│   │   ├── config.py           # Config loader/validator
│   │   ├── system_monitor.py   # CPU/RAM/disk monitoring
│   │   └── llm_client.py       # Llama.cpp client wrapper
│   │
│   ├── indexation/             # Indexing pipeline
│   │   ├── __init__.py
│   │   ├── scanner.py          # Filesystem scanner (FSEvents)
│   │   ├── queue.py            # JSON task queue
│   │   ├── worker.py           # Background worker (daemon)
│   │   ├── indexer.py          # Document indexer (orchestrator)
│   │   ├── text_extractor.py   # Direct text extraction (PDF, DOCX)
│   │   ├── exif_extractor.py   # EXIF metadata (images)
│   │   └── categorizer.py      # Auto-categorization (LLM)
│   │
│   ├── search/                 # Search engine
│   │   ├── __init__.py
│   │   ├── lancedb_client.py   # LanceDB wrapper
│   │   ├── meilisearch_client.py # Meilisearch wrapper
│   │   ├── hybrid_search.py    # Hybrid search (merge results)
│   │   └── ranking.py          # Custom ranking algorithms
│   │
│   ├── ocr/                    # OCR pipeline
│   │   ├── __init__.py
│   │   ├── router.py           # OCR router (decision logic)
│   │   ├── applescript_ocr.py  # macOS native OCR
│   │   ├── qwen_vl_ocr.py      # Qwen-VL OCR (tables)
│   │   └── table_detector.py   # Table detection (OpenCV)
│   │
│   ├── translation/            # Translation pipeline
│   │   ├── __init__.py
│   │   ├── translator.py       # LLM translator (zh-TW → fr/en)
│   │   └── action_extractor.py # Extract deadlines/actions
│   │
│   ├── api/                    # REST API
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── routes/
│   │   │   ├── search.py       # /api/search
│   │   │   ├── ingest.py       # /api/ingest
│   │   │   ├── translate.py    # /api/translate
│   │   │   ├── categories.py   # /api/categories
│   │   │   └── health.py       # /api/health, /api/stats
│   │   └── models.py           # Pydantic models
│   │
│   └── dashboard/              # CLI dashboard
│       ├── __init__.py
│       └── tui.py              # Rich TUI (status dashboard)
│
├── scripts/                    # One-shot scripts
│   ├── daily_scan.sh           # Cronjob script
│   ├── bench_qwen_vl_mmproj.py # OCR benchmarks (keep for reference)
│   ├── bench_paddle_ocr.py     # PaddleOCR (deprecated, garbage output)
│   └── migration/              # Data migration scripts
│
└── tests/
    ├── __init__.py
    ├── unit/                   # Unit tests (per module)
    │   ├── test_pathmanager.py
    │   ├── test_config.py
    │   ├── test_scanner.py
    │   └── ...
    ├── integration/            # Integration tests
    │   ├── test_indexing_pipeline.py
    │   ├── test_search_api.py
    │   └── ...
    └── e2e/                    # End-to-end tests
        ├── test_full_workflow.py
        └── fixtures/           # Test documents
```

---

### 3.2 Data & Logs (NOT Git-tracked, local only)

```
/Users/phil/Downloads/_sources/aitao/
├── models/                     # GGUF models, mmproj
│   ├── Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
│   ├── Qwen2.5-VL-7B-Instruct-mmproj-bf16.gguf
│   ├── qwen2.5-coder-7b-instruct-q4_k_m.gguf
│   └── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
│
├── logs/                       # JSON logs (rotation: 100MB)
│   ├── indexer.log
│   ├── ocr.log
│   ├── api.log
│   ├── worker.log
│   └── scanner.log
│
├── lancedb/                    # LanceDB vector database
│   └── aitao_documents/
│       ├── data/
│       └── metadata/
│
├── meilisearch/                # Meilisearch index (if local, not host)
│   └── data.ms
│
├── cache/                      # Cache files (OCR, translations)
│   ├── ocr/
│   │   └── {sha256}.json       # OCR results
│   └── translations/
│       └── {sha256}.json       # Translation results
│
├── queue/                      # JSON task queue
│   └── tasks.json
│
└── corrections/                # User feedback
    └── corrections.json
```

---

### 3.3 Test data (dev environment)

```
/Users/phil/Downloads/_Volumes/
├── test_pdf_scanned.pdf
├── test_table.jpg
├── test_chinese_doc.pdf
└── ...
```

---

## 4. Modules détaillés

### 4.1 Core Infrastructure

#### PathManager (`src/core/pathmanager.py`)

**Responsabilité:** Centraliser tous les accès filesystem.

**Interface:**
```python
class PathManager:
    """
    Central path management for AItao.
    All filesystem access MUST go through this module.
    """
    
    def __init__(self, config: ConfigManager):
        """Load paths from config.yaml."""
        pass
    
    def get_storage_root(self) -> Path:
        """Return storage root directory."""
        pass
    
    def get_models_dir(self) -> Path:
        """Return models directory."""
        pass
    
    def get_logs_dir(self) -> Path:
        """Return logs directory."""
        pass
    
    def get_queue_dir(self) -> Path:
        """Return queue directory."""
        pass
    
    def get_cache_dir(self, cache_type: str) -> Path:
        """Return cache directory (ocr, translations)."""
        pass
    
    def ensure_dirs(self):
        """Create all directories if they don't exist."""
        pass
```

**Dépendances:** ConfigManager

---

#### Logger (`src/core/logger.py`)

**Responsabilité:** Logging structuré JSON avec rotation.

**Interface:**
```python
class Logger:
    """
    Structured JSON logging for AItao.
    Separate log files per module.
    """
    
    def __init__(self, module_name: str, path_manager: PathManager):
        """Initialize logger for specific module."""
        pass
    
    def debug(self, message: str, **metadata):
        """Log debug message."""
        pass
    
    def info(self, message: str, **metadata):
        """Log info message."""
        pass
    
    def warning(self, message: str, **metadata):
        """Log warning message."""
        pass
    
    def error(self, message: str, **metadata):
        """Log error message."""
        pass
    
    def critical(self, message: str, **metadata):
        """Log critical message."""
        pass
```

**Format de log:**
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

**Dépendances:** PathManager

---

#### ConfigManager (`src/core/config.py`)

**Responsabilité:** Charger et valider `config.yaml`.

**Interface:**
```python
class ConfigManager:
    """
    Configuration loader and validator.
    Provides hot-reload support.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Load and validate config."""
        pass
    
    def get(self, key: str, default=None):
        """Get config value by dot notation (e.g., 'ocr.qwen_vl.model_path')."""
        pass
    
    def get_section(self, section: str) -> dict:
        """Get entire config section (e.g., 'search')."""
        pass
    
    def reload(self):
        """Reload config from file (hot-reload)."""
        pass
    
    def validate(self) -> bool:
        """Validate config schema."""
        pass
```

**Dépendances:** Aucune (core)

---

#### SystemMonitor (`src/core/system_monitor.py`)

**Responsabilité:** Monitorer ressources système (CPU, RAM, disk).

**Interface:**
```python
class SystemMonitor:
    """
    System resource monitor.
    Used to throttle background tasks based on system load.
    """
    
    def __init__(self, config: ConfigManager, logger: Logger):
        pass
    
    def get_cpu_percent(self) -> float:
        """Get current CPU usage (%)."""
        pass
    
    def get_memory_usage(self) -> dict:
        """Get memory usage: {used_gb, total_gb, percent}."""
        pass
    
    def get_disk_usage(self, path: Path) -> dict:
        """Get disk usage: {used_gb, total_gb, percent}."""
        pass
    
    def is_system_busy(self) -> bool:
        """Check if system is busy (CPU >80% or user active)."""
        pass
    
    def is_user_active(self) -> bool:
        """Detect user activity (macOS: mouse/keyboard events)."""
        pass
```

**Dépendances:** ConfigManager, Logger

---

### 4.2 Indexation Pipeline

#### FilesystemScanner (`src/indexation/scanner.py`)

**Responsabilité:** Scanner volumes pour détecter nouveaux/modifiés fichiers.

**Interface:**
```python
class FilesystemScanner:
    """
    Filesystem scanner for detecting new/modified documents.
    Supports FSEvents (macOS) for real-time watching.
    """
    
    def __init__(self, config: ConfigManager, logger: Logger):
        pass
    
    def scan_volumes(self, volumes: list[Path]) -> list[dict]:
        """
        Scan volumes and return list of new/modified files.
        Returns: [{path, mtime, sha256, size}]
        """
        pass
    
    def is_supported_file(self, path: Path) -> bool:
        """Check if file extension is supported."""
        pass
    
    def should_skip(self, path: Path) -> bool:
        """Check if file should be skipped (patterns)."""
        pass
    
    def watch_volumes(self, volumes: list[Path], callback):
        """Watch volumes for real-time changes (FSEvents)."""
        pass
```

**Dépendances:** ConfigManager, Logger

---

#### TaskQueue (`src/indexation/queue.py`)

**Responsabilité:** Queue JSON pour tâches d'indexation.

**Interface:**
```python
class TaskQueue:
    """
    JSON-based task queue for indexing operations.
    Thread-safe with file locking.
    """
    
    def __init__(self, path_manager: PathManager, logger: Logger):
        pass
    
    def add_task(self, file_path: Path, task_type: str, priority: str = "normal") -> str:
        """
        Add task to queue.
        Returns task ID (UUID).
        """
        pass
    
    def get_next_task(self) -> dict | None:
        """
        Get next pending task (highest priority).
        Returns: {id, file_path, task_type, priority, added_at, status}
        """
        pass
    
    def update_status(self, task_id: str, status: str, metadata: dict = None):
        """Update task status (pending → processing → completed/failed)."""
        pass
    
    def get_stats(self) -> dict:
        """Get queue stats: {pending, processing, completed, failed}."""
        pass
```

**Dépendances:** PathManager, Logger

---

#### BackgroundWorker (`src/indexation/worker.py`)

**Responsabilité:** Worker daemon qui traite la queue.

**Interface:**
```python
class BackgroundWorker:
    """
    Background worker daemon.
    Processes indexing tasks from queue with system load throttling.
    """
    
    def __init__(
        self,
        queue: TaskQueue,
        indexer: DocumentIndexer,
        system_monitor: SystemMonitor,
        logger: Logger
    ):
        pass
    
    def start(self):
        """Start worker daemon (infinite loop)."""
        pass
    
    def stop(self):
        """Stop worker gracefully."""
        pass
    
    def process_task(self, task: dict):
        """Process single task."""
        pass
    
    def should_process(self) -> bool:
        """Check if worker should process (system not busy)."""
        pass
```

**Dépendances:** TaskQueue, DocumentIndexer, SystemMonitor, Logger

---

### 4.3 Search Engine

#### LanceDBClient (`src/search/lancedb_client.py`)

**Responsabilité:** Wrapper LanceDB pour recherche vectorielle.

**Interface:**
```python
class LanceDBClient:
    """
    LanceDB client for semantic vector search.
    """
    
    def __init__(self, path_manager: PathManager, config: ConfigManager, logger: Logger):
        pass
    
    def add_document(self, doc: dict):
        """
        Add document to LanceDB.
        doc: {id, path, title, content, metadata}
        """
        pass
    
    def search(self, query: str, filters: dict = None, limit: int = 10) -> list[dict]:
        """
        Semantic search.
        Returns: [{id, path, title, summary, score, metadata}]
        """
        pass
    
    def delete(self, doc_id: str):
        """Delete document by ID."""
        pass
    
    def get_stats(self) -> dict:
        """Get stats: {total_docs, by_language, by_category}."""
        pass
```

**Dépendances:** PathManager, ConfigManager, Logger

---

#### MeilisearchClient (`src/search/meilisearch_client.py`)

**Responsabilité:** Wrapper Meilisearch pour recherche full-text.

**Interface:**
```python
class MeilisearchClient:
    """
    Meilisearch client for full-text search with filters.
    """
    
    def __init__(self, config: ConfigManager, logger: Logger):
        pass
    
    def add_document(self, doc: dict):
        """
        Add document to Meilisearch.
        doc: {id, path, title, content, metadata}
        """
        pass
    
    def search(self, query: str, filters: dict = None, limit: int = 10) -> list[dict]:
        """
        Full-text search with filters.
        Returns: [{id, path, title, summary, score, metadata}]
        """
        pass
    
    def delete(self, doc_id: str):
        """Delete document by ID."""
        pass
    
    def get_stats(self) -> dict:
        """Get stats: {total_docs, by_category, by_language}."""
        pass
```

**Dépendances:** ConfigManager, Logger

---

#### HybridSearch (`src/search/hybrid_search.py`)

**Responsabilité:** Combiner Meilisearch + LanceDB avec ranking pondéré.

**Interface:**
```python
class HybridSearch:
    """
    Hybrid search combining Meilisearch (full-text) + LanceDB (semantic).
    Weighted ranking: 40% Meilisearch, 60% LanceDB (configurable).
    """
    
    def __init__(
        self,
        meilisearch: MeilisearchClient,
        lancedb: LanceDBClient,
        config: ConfigManager,
        logger: Logger
    ):
        pass
    
    def search(self, query: str, filters: dict = None, limit: int = 10) -> list[dict]:
        """
        Hybrid search (parallel queries + merge).
        Returns: [{id, path, title, summary, score, metadata}]
        """
        pass
    
    def merge_results(
        self,
        meilisearch_results: list[dict],
        lancedb_results: list[dict]
    ) -> list[dict]:
        """Merge and rank results."""
        pass
```

**Dépendances:** MeilisearchClient, LanceDBClient, ConfigManager, Logger

---

### 4.4 OCR Pipeline

#### OCRRouter (`src/ocr/router.py`)

**Responsabilité:** Router OCR (choisir le bon moteur).

**Interface:**
```python
class OCRRouter:
    """
    OCR router: decide which OCR engine to use.
    Priority: direct text extraction > AppleScript OCR > Qwen-VL (tables).
    """
    
    def __init__(
        self,
        config: ConfigManager,
        logger: Logger,
        path_manager: PathManager
    ):
        pass
    
    def extract_text(self, file_path: Path) -> dict:
        """
        Extract text from document.
        Returns: {method, text, tables, metadata}
        """
        pass
    
    def try_direct_extraction(self, file_path: Path) -> dict | None:
        """Try direct text extraction (pdfminer, pypdf)."""
        pass
    
    def detect_tables(self, file_path: Path) -> bool:
        """Detect if document contains tables (OpenCV)."""
        pass
```

**Dépendances:** ConfigManager, Logger, PathManager

---

### 4.5 Translation Pipeline

#### Translator (`src/translation/translator.py`)

**Responsabilité:** Traduire zh-TW → fr/en.

**Interface:**
```python
class Translator:
    """
    LLM-based translator for Traditional Chinese → French/English.
    """
    
    def __init__(
        self,
        config: ConfigManager,
        logger: Logger,
        llm_client: LLMClient
    ):
        pass
    
    def translate(
        self,
        text: str,
        source_lang: str = "zh-TW",
        target_lang: str = "fr"
    ) -> dict:
        """
        Translate text.
        Returns: {translation, confidence}
        """
        pass
```

**Dépendances:** ConfigManager, Logger, LLMClient

---

### 4.6 REST API

#### FastAPI Application (`src/api/main.py`)

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Hybrid search |
| `/api/ingest` | POST | Manual file ingestion |
| `/api/translate` | POST | Translate document |
| `/api/categories` | GET | List categories |
| `/api/categories/{doc_id}` | PUT | Update category |
| `/api/queue` | GET | View queue status |
| `/api/health` | GET | Service health check |
| `/api/stats` | GET | Indexing stats |

**Documentation:** Auto-generated OpenAPI at `/docs`

---

## 5. Flux de données

### 5.1 Indexation automatique (Daily scan)

```
┌──────────────┐
│ Cronjob 2am  │
│ (daily_scan) │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ FilesystemScanner│
│ - Scan volumes   │
│ - Detect new/mod │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ TaskQueue        │
│ - Add tasks      │
│ (priority: normal│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ BackgroundWorker │
│ - Check system   │
│ - Process task   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ DocumentIndexer  │
│ - Extract text   │
│ - OCR if needed  │
│ - Categorize     │
└──────┬───────────┘
       │
       ├────────────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│ LanceDB      │  │ Meilisearch  │
│ (embeddings) │  │ (full-text)  │
└──────────────┘  └──────────────┘
```

---

### 5.2 Recherche (User query)

```
┌──────────────┐
│ User Query   │
│ (CLI/API)    │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ API /api/search  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ HybridSearch     │
│ - Parse filters  │
└──────┬───────────┘
       │
       ├────────────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Meilisearch  │  │ LanceDB      │
│ (full-text)  │  │ (semantic)   │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                ▼
       ┌──────────────────┐
       │ Merge & Rank     │
       │ (weighted)       │
       └──────┬───────────┘
              │
              ▼
       ┌──────────────────┐
       │ Return Results   │
       │ (top 10 + summary│
       └──────────────────┘
```

---

### 5.3 Ingestion manuelle (User request)

```
┌──────────────┐
│ User: ingest │
│ (CLI/API)    │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ TaskQueue        │
│ - Add task       │
│ (priority: HIGH) │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ BackgroundWorker │
│ - Skip queue     │
│ - Process now    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ DocumentIndexer  │
│ - Extract/OCR    │
│ - Translate?     │
│ - Categorize     │
└──────┬───────────┘
       │
       ├────────────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│ LanceDB      │  │ Meilisearch  │
└──────────────┘  └──────────────┘
```

---

## 6. Sécurité & Performance

### 6.1 Sécurité

- **Data locality:** 100% local, aucune donnée ne quitte la machine
- **Logs:** Stockés localement uniquement
- **API:** Pas d'auth en V1 (localhost only), JWT optionnel V2+
- **Chemins:** Pas de path traversal (validation via PathManager)

### 6.2 Performance

**Optimisations:**
1. **Parallel queries:** Meilisearch + LanceDB en parallèle
2. **Cache:** OCR et traductions cachées (évite retraitement)
3. **Throttling:** Worker pause si CPU >80%
4. **Embeddings batch:** Génération par batch (500 docs)
5. **Lazy loading:** Modèles LLM chargés à la demande

**Cibles:**
- Search latency: <3s (500K docs)
- Indexing throughput: 100 docs/h (texte), 10 docs/h (OCR)
- Memory footprint: <8GB

---

## 7. Monitoring & Observabilité

### 7.1 Logging

**Logs structurés JSON:**
- `indexer.log`: Indexation events
- `ocr.log`: OCR operations
- `api.log`: API requests/responses
- `worker.log`: Worker activity
- `scanner.log`: Filesystem scanning

**Rotation:** 100MB max par fichier

### 7.2 Metrics

**Collectées via API `/api/stats`:**
- Total documents indexés
- Documents par catégorie
- Documents par langue
- Queue length (pending, processing)
- Average search latency
- System resources (CPU, RAM, disk)

---

## 8. Déploiement

### 8.1 Installation

```bash
# Clone repo
git clone https://github.com/shamantao/aitao.git
cd aitao
git checkout pdr/v2-remodular

# Install dependencies (uv)
uv sync

# Configure
cp config/config.yaml.template config/config.yaml
# Edit config.yaml (volumes, paths)

# Start services
./aitao.sh start

# Verify
./aitao.sh status
```

### 8.2 Services

**Lancés par `aitao.sh start`:**
1. **API** (FastAPI, port 5000)
2. **Worker** (daemon, background)
3. **Cronjob** (daily scan, 2am)

**Arrêt propre:**
```bash
./aitao.sh stop
```

---

## 9. Migration de V1 vers V2

**Stratégie:** Fresh start (pas de migration données V1).

**Raisons:**
- V1 utilise AnythingLLM (Docker)
- V2 est architecture complètement différente
- Peu de données V1 à migrer (tests seulement)

**Si migration nécessaire (future):**
- Script `scripts/migration/v1_to_v2.py`
- Export LanceDB V1 → Import V2
- Rebuild Meilisearch index

---

## 10. Tests

### 10.1 Stratégie

1. **Unit tests:** Chaque module indépendamment
2. **Integration tests:** Pipelines complets
3. **E2E tests:** User workflows (ingest → search)

### 10.2 Coverage

**Cible:** >80% coverage

**CI/CD:** GitHub Actions (à configurer)

---

**Fin de l'architecture V2.0**
