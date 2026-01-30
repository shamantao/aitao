# ✅ Development Checklist

**Purpose:** Systematic checklist to prevent recurring errors identified in US-021b feedback (2026-01-30).

---

## 🔍 Pre-Development Phase

### 1. **Read NFR Requirements FIRST**

Before writing ANY code, read these PRD sections:

- **NFR-001:** Platform support (Python 3.13+, macOS/Linux)
- **NFR-006:** Dependency management (uv-first, never raw pip)
- **AC-001 to AC-005:** Architecture constraints
- **Specific US constraints:** Identified in US description

**Why:** Violations of NFR require systemic rework. Reading NFR prevents wasted effort.

**Action:** In your editor, open `prd/PRD.md` and scroll to NFR section BEFORE coding.

---

### 2. **Check Project Structure Conventions**

Before creating files, verify where they belong:

| File Type | Location | Example |
|-----------|----------|---------|
| Source code | `src/<module>/` | `src/llm/model_manager.py` |
| Tests (unit) | `tests/unit/` | `tests/unit/test_model_manager.py` |
| Tests (integration) | `tests/integration/` | `tests/integration/test_api.py` |
| Documentation | `docs/` | `docs/SUMMARY_US021b.md` |
| Config files | `config/` | `config/config.yaml` |
| Scripts | `scripts/` | `scripts/agent-code.py` |

**Why:** Files in wrong places become technical debt (must be moved later).

**Action:** Run `tree -L 2` to see structure BEFORE creating files.

---

### 3. **Verify Virtual Environment Setup**

Check that `.venv` exists and contains required tools:

```bash
# Check venv exists
ls -ld .venv/

# Check Python version
.venv/bin/python --version  # Must be Python 3.13+

# Check pytest installed
.venv/bin/python -m pytest --version

# Check uv installed
uv --version
```

**Why:** Using system `python` instead of `.venv/bin/python` violates NFR-006.

**Action:** If tools missing, run `./install.sh` or `uv sync`.

---

## 📝 During Development Phase

### 4. **Always Use .venv/bin/python**

**Never:**
```bash
❌ python my_script.py
❌ pytest tests/
❌ pip install package
```

**Always:**
```bash
✅ .venv/bin/python my_script.py
✅ .venv/bin/python -m pytest tests/
✅ uv add package
```

**Why:** System Python may lack dependencies, causing false negatives.

---

### 5. **Check API Signatures Before Using**

When using existing classes, verify their signatures:

```bash
# Example: Check StructuredLogger signature
grep -A 5 "def info" src/core/logger.py
```

**Common mistakes:**
- ❌ `logger.info("msg", key=value)` → Wrong (kwargs)
- ✅ `logger.info("msg", metadata={"key": value})` → Correct

- ❌ `OllamaClient(base_url=url)` → Wrong signature
- ✅ `OllamaClient(config=config, logger=logger)` → Correct

**Why:** API mismatches cause runtime errors that unit tests catch.

**Action:** Read class `__init__()` methods BEFORE instantiating.

---

### 6. **Write Tests Alongside Code**

For every new class/function, write tests IMMEDIATELY:

| Code File | Test File | Tests |
|-----------|-----------|-------|
| `src/llm/model_manager.py` | `tests/unit/test_model_manager.py` | 16+ |
| `src/api/routes/search.py` | `tests/integration/test_api_search.py` | 8+ |

**Why:** Writing tests later = forgotten edge cases.

**Action:** Create test file in same commit as implementation.

---

## ✅ Post-Development Phase

### 7. **Run ALL Tests Before Declaring Done**

**Minimum test suite:**
```bash
# Unit tests
.venv/bin/python -m pytest tests/unit/ -v

# Integration tests (if applicable)
.venv/bin/python -m pytest tests/integration/ -v

# Specific US tests
.venv/bin/python -m pytest tests/unit/test_model_manager.py -v
```

**Expected results:**
- ✅ All tests pass (green)
- ❌ If 1 test fails → NOT DONE (debug + fix)

**Why:** "Code compiles" ≠ "Code works". Tests prove functionality.

---

### 8. **Functional Validation with Real Tools**

After unit tests pass, test with REAL dependencies:

**Example (US-021b):**
```bash
# Real Ollama check
.venv/bin/python -m src.cli.main models status

# Real startup check
./aitao.sh start
```

**Why:** Mocks hide integration bugs. Real tools expose them.

**Action:** Include functional test results in SUMMARY.md.

---

### 9. **Update Documentation**

Before marking US as complete, verify docs exist:

| US | Required Docs |
|----|---------------|
| New feature | `docs/SUMMARY_US{id}.md` |
| New CLI | Update `docs/CLI_USAGE.md` |
| Architecture change | Update `prd/ARCHITECTURE.md` |

**Docs MUST include:**
- ✅ Summary (what was built)
- ✅ Files changed (with line counts)
- ✅ Test results (actual numbers, not placeholders)
- ✅ Examples (CLI commands with real output)

**Why:** Future debugging requires knowing what was implemented.

---

### 10. **Self-Review Against NFR**

Before submitting, re-read NFR and ask:

1. Did I use `.venv/bin/python` everywhere? (NFR-006)
2. Are files in correct folders? (Project conventions)
3. Did I run pytest? (Quality gates)
4. Does it work with real dependencies? (Functional validation)
5. Are docs updated? (Knowledge management)

**Why:** Prevents user from finding systemic issues (as in US-021b).

---

## 🚨 Red Flags That Indicate Checklist Was Skipped

If you see these patterns, STOP and review checklist:

1. **"Pytest not installed"** → Should have checked .venv (Step 3)
2. **File at repo root** → Should have checked structure (Step 2)
3. **TypeError at runtime** → Should have verified API signature (Step 5)
4. **"Tests ready to run"** → Should have RUN them (Step 7)
5. **No functional test** → Should have tested with real tools (Step 8)

---

## 📊 Success Metrics

A well-executed development cycle has:

- ✅ 0 NFR violations
- ✅ 0 files in wrong locations
- ✅ 100% test pass rate (X/X passed)
- ✅ Functional validation WITH real dependencies
- ✅ Complete documentation with actual results

**Benchmark:** US-021b (after corrections) achieved:
- 16/16 tests passed
- CLI functional with real Ollama
- All files in correct locations
- Documentation updated with real results

---

## 🔗 References

- **NFR Source:** `prd/PRD.md` (lines ~550-650)
- **Architecture:** `prd/ARCHITECTURE.md`
- **Test Framework:** `tests/conftest.py`
- **CLI Guide:** `docs/CLI_USAGE.md`

**Last Updated:** 2026-01-30 (Post US-021b feedback)
