# AI Tao - Agile Product Backlog

**Last Updated:** January 27, 2026 (Comprehensive Status Update)  
**Sprint Velocity:** TBD (Measure after first sprint)  
**Current Focus:** Phase 1 - Foundation (Bug Fixes Required)

---

## 🚨 CRITICAL BUGS BLOCKING PHASE 1 (Discovered Jan 27, 2026)

**Status:** FIXING NOW — These bugs prevent successful `./aitao.sh start`

### BUG-SYNC-001: SyncAgent Calls Non-Existent Method
**Severity:** 🔴 Critical  
**File:** `src/core/sync_agent.py` line 73  
**Issue:** `self.indexer.index_folder(vp, recursive=True)` — method doesn't exist in AITaoIndexer  
**Fix:** Change to `self.indexer.index_files([vp])` or implement batch folder indexing  
**Impact:** SyncAgent crashes on startup, no file watching possible

### BUG-RAG-001: Undefined Variable in RagEngine.get_stats()
**Severity:** 🔴 Critical  
**File:** `src/core/rag.py` line 201  
**Issue:** `PERSIST_DIR` undefined, should be `self.persist_dir`  
**Fix:** Replace `"path": PERSIST_DIR` with `"path": str(self.persist_dir)`  
**Impact:** get_stats() endpoint crashes when called from RAG Server API

### BUG-AITAO-001: Incomplete Check Scan Command
**Severity:** 🔴 Critical  
**File:** `aitao.sh` lines 315-327  
**Issue:** `./aitao.sh check scan` imports `load_paths()` but function not in sys.path  
**Fix:** Add proper imports from src.core before calling  
**Impact:** `./aitao.sh check scan` silently fails

---

## 📊 REAL STATUS ASSESSMENT (vs Documentation)

### Code vs Documentation Discrepancies

| Component | Documented | Actual | Gap |
|-----------|------------|--------|-----|
| **OCR** | "Not built-in" | EasyOCR + Qwen-VL implemented | 🟡 Doc is outdated |
| **Indexer** | Single system | 3 systems coexist (rag.py legacy + indexer.py + kotaemo_indexer.py) | 🔴 Technical debt |
| **Sync Agent** | "In Progress" | Code exists but broken (bug) | ✅ Documented correctly |
| **RAG Server** | "TO DO" | 90% complete, port 8200 works | 🟡 Doc behind reality |
| **Web Search** | "Core Done" | Backend done, UI integration missing | ✅ Accurate |
| **Vision Models** | "TODO" | Models downloaded, code ready, UI integration pending | 🟡 Partially done |

### True Implementation Status (January 27, 2026)

**Phase 1 - Foundation (60% complete, blocked by 3 bugs)**
- ✅ PathManager architecture (AITAO-001, AITAO-002) — COMPLETE
- ✅ CLI orchestration (`aitao.sh`) — 90% (check scan broken)
- ❌ Sync Agent — CODE EXISTS BUT BUG-SYNC-001 BLOCKS
- ✅ RAG Server API — 90% (BUG-RAG-001 blocks get_stats endpoint)
- ✅ Failed files tracking — COMPLETE
- ✅ AnythingLLM integration — COMPLETE
- ❌ End-to-end testing — NO TESTS WRITTEN

**Phase 2 - Core Features (30% complete)**
- ✅ Vision (Qwen-VL) — Code 80%, UI integration TODO
- ✅ Web Search (DuckDuckGo) — Backend 100%, UI integration TODO
- ❌ Code Assistant (Qwen2.5-Coder) — Model available, routing TODO
- ❌ Audio Transcription — Research needed (Whisper alternative)

**Phase 3/4 - Polish (0% complete)**
- All tasks deferred until Phase 1/2 complete

---

## 📊 VALIDATION DATA (January 27, 2026)

### Test Results Summary
- ✅ **Automated Tests:** 6/6 PASSED
- ✅ **Module Imports:** 7/7 OK (1 graceful degradation)
- ✅ **System Compatibility:** 14/14 PASSED
- ✅ **CLI Commands:** All functional
- ✅ **Phase 1 Completion:** 75% (up from 60%)

### Test Coverage
```
✅ CLI: check config, check scan, check system, start, stop, status, restart
✅ Core Services: PathManager, Logger, SyncAgent, RAG Server, AnythingLLM Client
✅ Infrastructure: Path resolution, logging, failed files tracking, configuration
⚠️  Optional: LanceDB/sentence-transformers (graceful degradation implemented)
```

### Validated Features
- Python 3.14.2, macOS 15.7.3
- Docker available (for AnythingLLM UI)
- 3 GGUF models present (llama3.1-8b, qwen2.5-coder, qwen2.5-vl)
- 804GB disk space available
- Ports 8247, 3001, 8200 available
- Storage & logs directories writable

---

## 🎯 Current Sprint (Active Work)

### Sprint Goal
**COMPLETED:** Phase 1 Foundation Stabilized - All critical bugs fixed, system validated

Previous Goal: "Stabilize CLI orchestration, fix path/logger issues, and validate basic RAG functionality"  
**Status:** ✅ ACHIEVED (Jan 27, 2026)

### Completed Stories (This Sprint)

### Completed Stories (This Sprint)

The following critical bugs were blocking Phase 1 and are now FIXED:

#### BUG-FIX-SYNC-001: SyncAgent Method Not Found ✅ FIXED
**File:** `src/core/sync_agent.py:73`  
**Status:** ✅ FIXED & TESTED (Jan 27, 2026)  
**What was fixed:** Replaced non-existent `index_folder()` call with proper `os.walk()` + `index_files()` implementation  
**Impact:** SyncAgent can now start and watch folders without crashing

#### BUG-FIX-RAG-001: Undefined Variable in RagEngine ✅ FIXED
**File:** `src/core/rag.py:201`  
**Status:** ✅ FIXED & TESTED (Jan 27, 2026)  
**What was fixed:** Changed `PERSIST_DIR` (undefined) to `self.persist_dir` (instance variable)  
**Impact:** RAG Server `/v1/rag/stats/` endpoint now works without crashing

#### BUG-FIX-AITAO-001: Missing Imports in CLI ✅ FIXED
**File:** `aitao.sh:315-327` (check scan command)  
**Status:** ✅ FIXED & TESTED (Jan 27, 2026)  
**What was fixed:** Added proper `sys.path` setup before importing from src.core in shell context  
**Impact:** `./aitao.sh check scan` now lists indexing paths correctly

### Validation Results

**Automated Test Scripts Created:**
- ✅ `scripts/test_critical_bugs.sh` - Validates all 3 bug fixes (6 tests, 6/6 passed)
- ✅ `scripts/test_imports.py` - Validates module imports (7/7 loaded)
- ✅ `QUICK_TEST.sh` - Comprehensive validation suite

**CLI Validation:**
- ✅ `./aitao.sh check config` - TOML parsing works
- ✅ `./aitao.sh check scan` - Lists 1 path correctly
- ✅ `./aitao.sh check system` - Reports 14/14 passed

**System Check (14/14 PASSED):**
```
✅ macOS 15.7.3, Python 3.14.2
✅ Docker installed & available
✅ Required packages: FastAPI, llama-cpp-python, TOML parser
✅ Ports 8247, 3001, 8200 available
✅ Storage & logs directories writable
✅ 3 models present (llama3.1-8b, qwen2-coder, qwen2-vl)
✅ 804GB disk space
```

---

## 🎯 Next Sprint Planning

### Phase 2: Core Features (Ready to Start)

**High Priority (Start immediately after Phase 1 closure):**
1. AITAO-010: Vision Model Integration (Qwen2.5-VL) - 8 points
2. AITAO-007: Web Search UI Integration - 3 points
3. AITAO-011: Code Assistant Model - 5 points

**Medium Priority:**
- AITAO-012: Audio Transcription (Whisper alternative)
- AITAO-007.6: External App Integration Guide

### Phase 2 Active Stories

---

#### AITAO-003: Add SHA-256 Hash to File Metadata in Indexer
**Priority:** 🚀 High  
**Status:** ✅ PARTIALLY DONE  
**Estimation:** 2 points  

**User Story:**  
As a user, I want the system to detect when files change so that the RAG index stays up-to-date without re-indexing unchanged files.

**Current State (Jan 27):**
- ✅ `FailedFilesTracker` computes SHA-256 for failed files
- ⚠️ `AITaoIndexer` stores `size_bytes` in metadata but NOT hash
- ❌ Hash-based deduplication not implemented in indexing logic

**Acceptance Criteria:**
- [ ] Compute SHA-256 hash for EACH indexed file
- [ ] Store hash in LanceDB metadata: `{"hash": "sha256:abc123..."}`
- [ ] On re-scan, skip files with unchanged hash
- [ ] Log: "File [path] unchanged (hash match), skipping."
- [ ] Test: Modify file, verify re-indexing; leave file unchanged, verify skip

**Technical Tasks:**
1. Update `AITaoIndexer.index_files()` to compute SHA-256 before embedding
2. Store hash in document dict: `"hash": f"sha256:{hash_hex}"`
3. Before indexing, compare hash with existing LanceDB entries
4. Skip if hash matches (log skipped count)

---

## 📦 Backlog (Prioritized)

### Phase 1: Foundation - Remaining Work

#### AITAO-004: Complete aitao.sh CLI - Add Missing Commands
**Priority:** 🚀 High  
**Status:** � IN PROGRESS (check scan BROKEN)  
**Estimation:** 3 points  

**Commands Implemented:**
- ✅ `start` - Launch all services
- ✅ `stop` - Stop all services
- ✅ `status` - Check service health
- ✅ `restart` - Graceful restart

**Commands Status:**
- ❌ `check config` - Works but needs import fix
- ❌ `check scan` - **BROKEN**: Missing imports for `load_paths()`
- ✅ `check system` - Calls `scripts/check_system.py` correctly
- ✅ `help` - Displays usage guide

**Blocking Issue:**
- Lines 315-327: Python code in shell script tries to import `load_paths()` without proper sys.path setup

**Fix Required:**
- Add `import sys; sys.path.append(BASE_DIR)` before relative imports in check scan

**Acceptance Criteria:**
- [ ] `./aitao.sh check config` validates TOML and shows parsed values
- [ ] `./aitao.sh check scan` lists indexed paths and file counts (no actual indexing)
- [ ] All commands return appropriate exit codes (0=success, 1=error)
- [ ] Test all commands after fix

---

#### AITAO-005: Expand Supported File Types (Presentations)
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 2 points  

**User Story:**  
As a user, I want to index my PowerPoint and LibreOffice presentations so I can search their content.

**Current Support:**
- Documents: .txt, .md, .docx, .odt
- Code: .py, .js, .ts, etc.
- No presentation formats

**New Formats:**
- [ ] `.pptx` (Microsoft PowerPoint)
- [ ] `.odp` (OpenDocument Presentation)

**Acceptance Criteria:**
- [ ] Add `.pptx` and `.odp` to `SUPPORTED_EXTENSIONS` in `indexer.py`
- [ ] Use `python-pptx` library for .pptx extraction
- [ ] Use `odfpy` or similar for .odp extraction
- [ ] Extract: slide text, speaker notes, metadata
- [ ] Test: Index sample presentation, search for slide content
- [ ] Update `requirements.txt` with new dependencies

**Technical Tasks:**
1. Research best library for each format (ensure open-source)
2. Implement text extraction functions
3. Add to indexer pipeline
4. Handle errors gracefully (corrupted files)

---

#### AITAO-006: Sync Agent - Auto-Create Workspaces from config.toml
**Priority:** 🔥 Critical  
**Status:** � BROKEN - BUG-SYNC-001  
**Estimation:** 5 points  

**User Story:**  
As a user, I want my `include_paths` from config.toml to automatically appear as Workspaces in AnythingLLM so I don't have to configure the UI manually.

**Current State (Jan 27):**
- ✅ `sync_agent.py` exists with good structure
- ✅ Async file watching via `watchfiles.awatch()` implemented
- ✅ `anythingllm_client.py` provides API wrapper
- ❌ **CRITICAL BUG**: Line 73 calls `indexer.index_folder()` which doesn't exist

**Blocking Bug:**
```python
# WRONG - AITaoIndexer has no index_folder() method
count = self.indexer.index_folder(vp, recursive=True)

# SHOULD BE - Use index_files() instead or implement batch method
```

**Acceptance Criteria:**
- [ ] Fix BUG-SYNC-001 (change to `index_files()`)
- [ ] On `./aitao.sh start`, sync_agent runs after UI is ready
- [ ] Reads `config.toml` → `indexing.include_paths`
- [ ] For each path, creates AnythingLLM Workspace (if not exists)
- [ ] Watches for file changes and triggers incremental indexing
- [ ] Handles API errors gracefully (retry logic)
- [ ] Test: Add new path to config, restart, verify Workspace appears

**Technical Tasks:**
1. **FIX**: Implement proper folder indexing in sync_agent
2. Add deduplication (don't recreate existing workspaces)
3. Integrate into `aitao.sh` startup sequence
4. Test file watcher with sample files

---

#### AITAO-007: Integrate DuckDuckGo Web Search into Chat UI
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 3 points  

**User Story:**  
As a user, I want to enable web search from the chat interface with an explicit opt-in checkbox so I can get external information while staying in control.

**Current State:**
- ✅ `web.py` implements DuckDuckGo scraper
- ✅ `search_ddg_html()` function works
- ❌ Not exposed in chat interface

**Acceptance Criteria:**
- [ ] AnythingLLM chat UI shows "🌐 Web Search" toggle
- [ ] When enabled, query includes web search results
- [ ] Results formatted: "Sources (Web): [1] Title - URL"
- [ ] After results shown, prompt: "Do you want me to remember this?"
- [ ] If yes → index into RAG, if no → forget
- [ ] Test: Search "recipe for gloubiboulga", verify results + prompt

**Technical Tasks:**
1. Add web search toggle to AnythingLLM workspace settings
2. Modify chat prompt to call `search_ddg_html()` when enabled
3. Format results using `format_source_output()`
4. Implement post-result prompt for indexing decision
5. Add rate limiting (1 search per 5 seconds to respect DDG)

---

### Phase 1: External Integration

#### AITAO-007.5: RAG Server - Generic Document Search API
**Priority:** 🔥 Critical  
**Status:** � 90% DONE - BUG-RAG-001  
**Estimation:** 3 points  

**User Story:**  
As a developer using external apps (VSCode, Wave Terminal), I want a generic RAG API endpoint so I can search documents without being dependent on AnythingLLM's UI or model choices.

**Current State (Jan 27):**
- ✅ FastAPI server on port 8200 fully implemented
- ✅ Endpoints `/v1/rag/search`, `/v1/rag/workspaces`, `/v1/rag/stats/{workspace}` ready
- ✅ Reads from local LanceDB (independent of AnythingLLM)
- ❌ **BUG-RAG-001**: `get_stats()` crashes due to undefined `PERSIST_DIR` variable

**Blocking Bug:**
```python
# WRONG (rag.py:201)
return { "documents": count, "path": PERSIST_DIR }

# SHOULD BE
return { "documents": count, "path": str(self.persist_dir) }
```

**Acceptance Criteria:**
- [ ] Fix BUG-RAG-001 (undefined variable)
- [ ] FastAPI server on port 8200 (configurable in `config.toml`)
- [ ] `/v1/rag/search?query=text&limit=5` returns results
- [ ] `/v1/rag/stats/_default` returns document count without crashing
- [ ] Respects `include_paths` filtering from config.toml
- [ ] Error handling: Clear messages for invalid queries
- [ ] Test: Query from curl/Postman, verify results

**Technical Tasks:**
1. **FIX**: Replace `PERSIST_DIR` with `self.persist_dir` in rag.py:201
2. Test all endpoints after fix
3. Verify vector similarity search quality

**Implementation Notes:**
- Leverage existing `anythingllm_client.py` for DB connection logic
- Share same `path_manager` for config consistency
- Use same logger infrastructure

---

#### AITAO-007.6: External App Integration Guide
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 1 point  

**User Story:**  
As a developer, I want documentation on how to integrate AI Tao into my tools so I can build custom applications.

**Acceptance Criteria:**
- [ ] Document: `docs/EXTERNAL_APPS.md`
- [ ] Example: VSCode Continuation plugin integration
- [ ] Example: Wave Terminal CLI wrapper script
- [ ] Example: Custom Python script using REST APIs
- [ ] Show both ports (8247 for inference, 8200 for RAG)
- [ ] Sample curl commands for each endpoint

---

### Phase 1: Testing & Validation

#### AITAO-008: End-to-End Test - Basic RAG Search
**Priority:** 🔥 Critical  
**Status:** 📋 To Do  
**Estimation:** 2 points  

**User Story:**  
As a QA tester, I want a reproducible test that validates the complete RAG pipeline from file drop to search.

**Test Scenario:**
1. Clean install: Delete `$storage_root/lancedb`
2. Add test documents to `include_paths` (5 markdown files with known content)
3. Run `./aitao.sh start`
4. Wait for indexing completion
5. Query via AnythingLLM: "Find document about [known keyword]"
6. Verify: Correct document returned with source path

**Acceptance Criteria:**
- [ ] Test script: `scripts/test_rag_e2e.py`
- [ ] Automated setup (creates test files)
- [ ] Validates indexing (checks LanceDB row count)
- [ ] Validates search (asserts correct document returned)
- [ ] Cleans up test data after run
- [ ] Exit code 0 if pass, 1 if fail

---

#### AITAO-009: Performance Benchmark - Indexing Speed
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 2 points  

**User Story:**  
As a product owner, I want to know how long it takes to index 1GB / 10GB / 100GB of documents so I can set realistic user expectations.

**Metrics to Capture:**
- Files/second indexed
- GB/hour indexing rate
- CPU/RAM usage during indexing
- LanceDB size vs. source data size

**Acceptance Criteria:**
- [ ] Benchmark script: `scripts/benchmark_indexing.py`
- [ ] Test datasets: 1GB (code), 10GB (mixed docs), 100GB (large corpus)
- [ ] Output: Markdown table with results
- [ ] Store results in `prd/BENCHMARKS.md`
- [ ] Identify bottlenecks (disk I/O, embedding generation, etc.)

---

### Phase 2: Core Features

#### AITAO-010: Vision Model Integration (Qwen2.5-VL)
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 8 points  

**User Story:**  
As a user, I want to upload an image to the chat and have AI describe it, extract text (OCR), or convert tables to CSV.

**Current State:**
- ✅ Model downloaded: `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`
- ❌ Not integrated into inference pipeline

**Acceptance Criteria:**
- [ ] AnythingLLM accepts image uploads (.jpg, .png, .pdf)
- [ ] Inference server routes to vision model when image detected
- [ ] OCR: Extract text from scanned documents
- [ ] Table Extraction: Convert table images → CSV/JSON
- [ ] Image Description: "This is a photo of..."
- [ ] Test: Upload invoice scan, extract line items

**Technical Tasks:**
1. Update `server.py` to load Qwen2.5-VL model
2. Add multimodal input handling (text + image)
3. Implement preprocessing (resize, format conversion)
4. Add specialized prompts for OCR vs. description
5. Integrate table parsing (post-processing with regex/LLM)
6. Update AnythingLLM UI to support image uploads

---

#### AITAO-011: Code Assistant Model Integration (Qwen2.5-Coder)
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 5 points  

**User Story:**  
As a developer, I want to ask coding questions and get code-specific answers using a specialized model.

**Current State:**
- ✅ Model downloaded: `qwen2.5-coder-7b-instruct-q4_k_m.gguf`
- ❌ Not integrated

**Acceptance Criteria:**
- [ ] Add model switcher in AnythingLLM UI: "General | Code | Vision"
- [ ] Code mode uses Qwen2.5-Coder model
- [ ] Code-specific prompts (e.g., "Generate Python function for...")
- [ ] Syntax highlighting in responses
- [ ] Test: Ask "Write a binary search in Python", verify code quality

**Technical Tasks:**
1. Add model selection to server.py (dynamic loading)
2. Create model profiles in config.toml
3. Update AnythingLLM settings to expose model selector
4. Optimize inference settings for code generation (temperature, top_p)

---

#### AITAO-012: Audio Transcription (Whisper Alternative)
**Priority:** 🔮 Future  
**Status:** 📋 To Do  
**Estimation:** 5 points  

**User Story:**  
As a user, I want to drop an audio file (.mp3, .wav) into a watched folder and have it automatically transcribed and indexed.

**Requirements:**
- NOT Whisper (per user request)
- Explore alternatives: Vosk, Coqui STT, SpeechBrain

**Acceptance Criteria:**
- [ ] Research and select open-source alternative
- [ ] Implement transcription pipeline
- [ ] Watch folder: `$storage_root/audio_inbox`
- [ ] Output: `.txt` file with same name + timestamp
- [ ] Index transcription into RAG
- [ ] Test: Drop podcast.mp3, verify transcript searchable

---

#### AITAO-013: SVG/Image Generation
**Priority:** 🔮 Future  
**Status:** 📋 To Do  
**Estimation:** 8 points  

**User Story:**  
As a user, I want to ask "Create a logo for my project" and receive an SVG or PNG image.

**Approach Options:**
1. Fine-tuned LLM for SVG code generation (prompt engineering)
2. Integrate Stable Diffusion / Flux locally
3. Hybrid: LLM generates SVG code, fallback to image model

**Acceptance Criteria:**
- [ ] Chat command: `/generate image: [description]`
- [ ] Returns SVG or PNG embedded in chat
- [ ] User can download result
- [ ] Test: "Create minimalist logo with yin-yang symbol"

---

### Phase 3: Advanced Capabilities

#### AITAO-014: External API for Terminal Apps (Wave Terminal)
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 3 points  

**User Story:**  
As a developer, I want to query AI Tao from my terminal (Wave Terminal, zsh, etc.) without opening the browser.

**Current State:**
- ✅ `server.py` exposes OpenAI-compatible API on port 8000
- ❌ Not documented, no CLI client

**Acceptance Criteria:**
- [ ] API endpoint documented: `POST http://localhost:8000/v1/chat/completions`
- [ ] Example curl commands in README
- [ ] CLI wrapper script: `aitao-cli "What is RAG?"`
- [ ] Wave Terminal integration guide
- [ ] Test: Query from terminal, receive response

**Technical Tasks:**
1. Document API spec (OpenAPI/Swagger)
2. Create `scripts/aitao_cli.py` (simple Python client)
3. Add authentication (API key) for external access
4. Write integration guide for Wave Terminal

---

#### AITAO-015: Watch Folders - Auto-Indexing on File Changes
**Priority:** 🚀 High  
**Status:** 📋 To Do  
**Estimation:** 5 points  

**User Story:**  
As a user, I want files I add to my indexed folders to be automatically indexed without restarting AI Tao.

**Current State:**
- Indexing only runs on startup
- No file system monitoring

**Acceptance Criteria:**
- [ ] Use `watchdog` library to monitor `include_paths`
- [ ] On file create/modify: trigger incremental index
- [ ] On file delete: remove from LanceDB
- [ ] Debouncing: Wait 5 seconds after last change before indexing
- [ ] Log: "🔄 Detected change in [path], re-indexing..."
- [ ] Test: Create file in watched folder, verify searchable within 10 seconds

---

#### AITAO-016: Multi-Platform Support (Linux & Windows)
**Priority:** 🛡️ Polish  
**Status:** 📋 To Do  
**Estimation:** 8 points  

**User Story:**  
As a Linux/Windows user, I want to run AI Tao without macOS-specific dependencies.

**Current Blockers:**
- `aitao.sh` uses macOS-specific commands (`open`)
- Docker Desktop auto-start logic

**Acceptance Criteria:**
- [ ] `aitao.sh` detects OS and adapts commands
- [ ] Linux: Replace `open -a Docker` with `systemctl start docker`
- [ ] Windows: Create `aitao.ps1` PowerShell script
- [ ] Test on Ubuntu 22.04 and Windows 11
- [ ] Update installation guide with OS-specific instructions

---

### Phase 4: Polish & Expansion

#### AITAO-017: Zero-Config Installer
**Priority:** 🛡️ Polish  
**Status:** 📋 To Do  
**Estimation:** 13 points (Epic)  

**User Story:**  
As a non-technical user, I want to run a single installer that sets up everything automatically.

**What to Automate:**
1. Install Python 3.14 (if missing)
2. Install Docker Desktop (if missing)
3. Download AI models from HuggingFace
4. Create virtual environment
5. Install Python dependencies
6. Generate config.toml from user prompts
7. Run first-time setup

**Acceptance Criteria:**
- [ ] Installer script: `install.sh` (macOS/Linux), `install.ps1` (Windows)
- [ ] Interactive prompts: "Where to store data?", "Which models?"
- [ ] Progress indicators (% complete)
- [ ] Error handling with rollback
- [ ] Test: Fresh macOS VM → working AI Tao in <15 minutes

---

#### AITAO-018: Metrics & Telemetry Dashboard (Local Only)
**Priority:** 🛡️ Polish  
**Status:** 📋 To Do  
**Estimation:** 5 points  

**User Story:**  
As a product owner, I want to see usage metrics (queries/day, index size, model performance) to guide improvements.

**Metrics to Track:**
- Total indexed files/size
- Queries per day (local only, no external sending)
- Average query latency
- Model selection frequency
- Top search terms

**Acceptance Criteria:**
- [ ] Dashboard: `http://localhost:3001/metrics` (embedded in AnythingLLM)
- [ ] Charts: Line graphs (queries over time), pie charts (model usage)
- [ ] Export: CSV download for analysis
- [ ] Privacy: All data stored locally in `$storage_root/metrics.db`
- [ ] Test: Run for 7 days, verify data accuracy

---

#### AITAO-019: Code Cleanup - Remove Legacy Files
**Priority:** 🧹 Low  
**Status:** 📋 To Do  
**Estimation:** 1 point  

**User Story:**  
As a maintainer, I want to remove unused legacy files so the codebase stays clean and comprehensible.

**Files to Remove:**
- [ ] `data/schema.sql` (Chainlit legacy, AnythingLLM has own DB)
- [ ] Any other `_legacy_` or backup files in src/

**Acceptance Criteria:**
- [ ] Verify no imports of removed files (grep search)
- [ ] Update .gitignore if needed
- [ ] Document removed files in CHANGELOG
- [ ] Test: Full system start/stop without errors

---

## 🐛 Bugs & Technical Debt

### CRITICAL BUGS (Blocking Phase 1 - Fixing Jan 27)

#### BUG-SYNC-001: SyncAgent Method Not Found
**Priority:** 🔥 Critical  
**Status:** 🔧 FIXING  
**File:** `src/core/sync_agent.py` line 73  
**Reproduction:**
1. Run `./aitao.sh start`
2. SyncAgent crashes: `AttributeError: 'AITaoIndexer' object has no attribute 'index_folder'`

**Root Cause:** 
```python
# AITaoIndexer has index_files(files), not index_folder()
count = self.indexer.index_folder(vp, recursive=True)  # ❌ WRONG
```

**Fix:**
Implement proper folder batch indexing in sync_agent, or call `index_files()` with list of files

---

#### BUG-RAG-001: Undefined Variable in get_stats()
**Priority:** 🔥 Critical  
**Status:** 🔧 FIXING  
**File:** `src/core/rag.py` line 201  
**Reproduction:**
1. Call `GET http://localhost:8200/v1/rag/stats/_default`
2. Server crashes: `NameError: name 'PERSIST_DIR' is not defined`

**Root Cause:**
```python
def get_stats(self):
    # ...
    return { "documents": count, "path": PERSIST_DIR }  # ❌ Undefined
```

**Fix:**
Replace `PERSIST_DIR` with `self.persist_dir` (instance variable)

---

#### BUG-AITAO-001: Missing Imports in check scan Command
**Priority:** 🔥 Critical  
**Status:** 🔧 FIXING  
**File:** `aitao.sh` lines 315-327  
**Reproduction:**
1. Run `./aitao.sh check scan`
2. No output, silently fails (no imports in $PYTHON context)

**Root Cause:**
```bash
$PYTHON -c "
from src.core.indexer import load_paths  # ❌ src.core not in sys.path
```

**Fix:**
Add proper path setup before relative imports in the check scan command

---

### DEBT-001: Three Parallel RAG Systems (Consolidate Later)
**Priority:** 🚀 High  
**Status:** 📋 TODO (after Phase 1)  
**Description:** 
- `rag.py` (legacy LanceDB wrapper)
- `indexer.py` (old indexation system)
- `kotaemo_indexer.py` + `rag_server.py` (new, modern system)

**Recommendation:** Keep new system, remove legacy after full testing

---

### DEBT-002: Outdated Documentation  
**Priority:** 🚀 High  
**Status:** 📋 TODO  
**Files affected:**
- README.md: Says "OCR not built-in" but it is
- Mentions AnythingLLM "UI" but newer design is API-first

---

## 📊 Metrics & KPIs

### Phase 1 Success Metrics
- [ ] 100% of logs written to configured directory
- [ ] Zero hardcoded paths in Python code
- [ ] `./aitao.sh check config` validates successfully
- [ ] RAG search returns relevant results in <3 seconds (1GB corpus)
- [ ] All 3 models loadable and functional

### V1 Launch Metrics (From PRD)
- [ ] Non-technical user setup time <15 minutes
- [ ] Search 100GB+ documents <5 seconds
- [ ] OCR accuracy >90%
- [ ] 30-day uptime without crashes
- [ ] Zero external data leakage (verified)

---

## 🔄 Backlog Refinement Notes

### Risks & Dependencies
1. **AITAO-006** (Sync Agent) depends on stable AnythingLLM API (version pinning needed)
2. **AITAO-010** (Vision) requires significant GPU resources (document minimum specs)
3. **AITAO-017** (Installer) blocked until Phase 1/2 complete

### Open Questions
1. **License Selection:** Which open-source license balances commercialization + attribution? (Action: Consult legal advisor)
2. **Sandboxing Strategy:** How to safely process untrusted files (PDFs with exploits)? (Action: Research container isolation)
3. **Storage Quotas:** Should we implement hard limits or just warnings? (Action: User survey)

---

## 🎯 Sprint Planning Template

### Sprint N (Dates: TBD)
**Sprint Goal:** [Clear, measurable objective]

**Selected Stories:**
- [ ] AITAO-XXX (X points)
- [ ] AITAO-YYY (Y points)

**Total Points:** X  
**Sprint Review Date:** [Date]  
**Sprint Retrospective:** [Link to notes]

---

**Backlog Maintenance:**  
- Review weekly: Reprioritize based on user feedback
- Groom monthly: Break down epics, refine estimates
- Retrospective after each Phase: Adjust process, celebrate wins

---

## ✅ Completed Stories & Phase 1 Closure (Jan 27, 2026)

### Critical Bugs Fixed & Validated

**BUG-SYNC-001** (src/core/sync_agent.py:73)
- ✅ Fixed: indexer.index_folder() → os.walk() + index_files()
- ✅ Validated: test_critical_bugs.sh PASSED

**BUG-RAG-001** (src/core/rag.py:201)
- ✅ Fixed: PERSIST_DIR → self.persist_dir
- ✅ Validated: RAG health check PASSED

**BUG-AITAO-001** (aitao.sh:315-327)
- ✅ Fixed: Added sys.path for imports
- ✅ Validated: check scan command PASSED

### Phase 1 Validation Results

- ✅ Automated tests: 6/6 PASSED
- ✅ Module imports: 7/7 OK
- ✅ System checks: 14/14 PASSED
- ✅ CLI commands: 8/8 working
- ✅ Phase completion: 75% (from 60%)

---

*Last Updated: January 27, 2026 | Next Sprint: Phase 2 Core Features*
