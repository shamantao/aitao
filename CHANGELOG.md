# Changelog

All notable changes to AiTao will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adopts [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting from version `2.5.1`.

---

## [Unreleased]

### Added
- `CHANGELOG.md` — this file (tao-init standard, US-045)
- `SECURITY.md` — security policy (tao-init standard)

---

## [2.5.1] — 2026-03-10

### Changed
- **Config format: YAML → TOML** (US-045)
  - `config/config.yaml` and `config/config.yaml.template` replaced by
    `config/config.toml` and `config/config.toml.template`
  - `src/core/config.py` rewritten: layered TOML loader aligned with
    tao-init v1.0.0 (stdlib `tomllib`, env var overrides `APP__SECTION__KEY`)
  - `src/core/pathmanager.py`, `src/indexation/worker.py`,
    `src/indexation/scanner.py`, `src/indexation/text_extractor.py`,
    `src/cli/utils.py`, `src/cli/commands/config.py`,
    `src/search/meilisearch_client.py`, `install.sh` all updated
  - All unit tests and e2e tests migrated to TOML fixtures
- **Version scheme: custom → SemVer** (internal decision 2026-03-10)
  - Former scheme `Major.Sprint.US.patch` replaced by `MAJOR.MINOR.PATCH`
  - `pyproject.toml` version: `2.6.38.3` → `2.5.1`

### Fixed
- YAML `\&` escape error in `config/config.yaml` line 53
  (`${HOME}/pCloudSync/Commun_Tzu-Yin\&Phil/…` — now a non-issue in TOML)

---

## [2.5.0] — 2026-01-28  *(retroactive label — was "Epic 10 ARM64")*

### Added
- ARM64 (Apple Silicon) support for portable installation
- `aitao-Install-Windows/portable/arm64/` setup scripts

---

## [2.4.0] — 2026-01-15  *(retroactive label — was "Sprint 4")*

### Added
- RAG engine (`src/llm/rag_engine.py`)
- LanceDB vector store integration
- Hybrid search (keyword + vector)

---

## [2.3.0] — 2025-12-01  *(retroactive label — was "Sprint 3")*

### Added
- MeiliSearch integration (`src/search/meilisearch_client.py`)
- Background indexation worker (`src/indexation/worker.py`)
- Task queue system

---

## [2.2.0] — 2025-11-01  *(retroactive label — was "Sprint 2 + 2b")*

### Added
- File system scanner (`src/indexation/scanner.py`)
- Text extractor with OCR support (`src/indexation/text_extractor.py`)
- Virtual model routing (`src/api/virtual_models.py`)

---

## [2.1.0] — 2025-10-01  *(retroactive label — was "Sprint 1")*

### Added
- CLI interface (`src/cli/`)
- PathManager (`src/core/pathmanager.py`)
- ConfigManager YAML-based loader (now replaced in 2.5.1)
- Ollama client (`src/llm/ollama_client.py`)

---

## [2.0.0] — 2025-09-01  *(retroactive label — was "Sprint 0")*

### Added
- Initial project scaffold (AiTao v2)
- Docker support (`Dockerfile`)
- Installation script (`install.sh`)

---

[Unreleased]: https://github.com/your-org/aitao/compare/v2.5.1...HEAD
[2.5.1]: https://github.com/your-org/aitao/compare/v2.5.0...v2.5.1
[2.5.0]: https://github.com/your-org/aitao/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/your-org/aitao/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/your-org/aitao/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/your-org/aitao/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/your-org/aitao/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/your-org/aitao/releases/tag/v2.0.0
