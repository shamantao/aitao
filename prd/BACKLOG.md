# AItao V2.0 - Backlog Agile

**Date:** January 30, 2026  
**Branch:** `pdr/v2-remodular`  
**Priorité:** MOSCOW (Must/Should/Could/Won't)  
**Version actuelle:** 2.3.21.5 (Sprint Q&A Complete ✅)

---

## 🏁 Sprint Summary

| Sprint | Status | User Stories | Tests | Version |
|--------|--------|--------------|-------|---------|
| Sprint 0: Foundation | ✅ Complete | US-001 → US-007b | 85 | v2.0.5 → v2.1.8 |
| Sprint 1: Indexation | ✅ Complete | US-008 → US-010 | 218 | v2.1.9 → v2.1.11 |
| Sprint 2: Recherche | ✅ Complete | US-011 → US-015 | 370 | v2.2.11 → v2.2.15 |
| Sprint 3: RAG & LLM | ✅ Complete | US-016 → US-021 | 461 | v2.3.16 → v2.3.20 |
| **Sprint Q&A: Vérifications** | 🔍 In Progress | QA-001 → QA-006 | - | v2.3.21.x |
| Sprint 4: OCR & Extraction | 📋 Pending | US-022 → US-026 | - | v2.4.x |
| Sprint 5: Traduction | 📋 Pending | US-027 → US-029 | - | v2.5.x |
| Sprint 6: Catégorisation | 📋 Pending | US-030 → US-032 | - | v2.6.x |
| Sprint 7: Dashboard & Polish | 📋 Pending | US-033 → US-037 | - | v2.7.x |

---

## Sprint 0: Foundation (2 semaines - Fév 2026)

### Epic 1: Core Architecture ✅

#### US-001: Créer le PathManager [MUST] ✅ DONE
**En tant que** développeur  
**Je veux** un gestionnaire centralisé de chemins  
**Afin de** ne jamais hard-coder des chemins absolus dans le code

**Critères d'acceptation:**
- [x] Classe `PathManager` dans `src/core/pathmanager.py`
- [x] Méthodes: `get_storage_root()`, `get_models_dir()`, `get_logs_dir()`, `get_queue_dir()`, `get_cache_dir()`
- [x] Lit les chemins depuis `config.yaml` (actuellement config.toml)
- [x] Crée les répertoires s'ils n'existent pas
- [x] Tests unitaires pour tous les chemins (12 tests passent)

**Estimation:** 2 points  
**Dépendances:** Aucune  
**Commit:** `1a11c18` - Date: 2026-01-28

---

#### US-002: Créer le Logger [MUST] ✅ DONE
**En tant que** développeur  
**Je veux** un logger structuré en JSON  
**Afin de** faciliter le debugging et le monitoring

**Critères d'acceptation:**
- [x] Classe `Logger` dans `src/core/logger.py`
- [x] Format JSON avec timestamp, level, module, message, metadata
- [x] Rotation des logs (100MB max par fichier)
- [x] Logs séparés par module (indexer.log, ocr.log, api.log)
- [x] Niveaux: DEBUG, INFO, WARNING, ERROR, CRITICAL
- [x] Tests unitaires (14 tests passent)

**Estimation:** 3 points  
**Dépendances:** US-001 (PathManager)  
**Commit:** `3e6781c` - Date: 2026-01-28

---

#### US-003: Créer le ConfigManager [MUST] ✅ DONE
**En tant que** développeur  
**Je veux** un gestionnaire de configuration centralisé  
**Afin de** charger et valider `config.yaml`

**Critères d'acceptation:**
- [x] Classe `ConfigManager` dans `src/core/config.py`
- [x] Charge `config.yaml` avec validation de schéma
- [x] Fournit des valeurs par défaut
- [x] Hot-reload sur modification du fichier
- [x] Méthodes: `get(key)`, `get_section(name)`, `reload()`
- [x] Tests unitaires avec fixtures (19 tests passent)

**Estimation:** 3 points  
**Dépendances:** US-001 (PathManager)  
**Commit:** `e0fbb01` - Date: 2026-01-28

---

#### US-004: Créer config.yaml [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** un fichier de configuration unique  
**Afin de** configurer tous les aspects d'AItao

**Critères d'acceptation:**
- [x] Fichier `config/config.yaml` avec schema complet (voir PRD FR-002)
- [x] Sections: paths, indexing, ocr, translation, search, categories, api, resources, logging
- [x] Variables d'environnement supportées (ex: `${HOME}`)
- [x] Documentation inline (commentaires YAML)
- [x] Fichier template `config.yaml.template` pour installation

**Estimation:** 2 points  
**Dépendances:** Aucune  
**Commit:** (en cours) - Date: 2026-01-28

---

#### US-005: Créer CLI aitao.sh [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** un script shell pour gérer AItao  
**Afin de** démarrer/arrêter/vérifier les services

**Critères d'acceptation:**
- [x] Script `aitao.sh` avec commandes: start, stop, status, ingest, search, logs, config
- [x] `aitao.sh start`: Lance API, worker, cronjob (placeholder pour Sprint 5)
- [x] `aitao.sh stop`: Arrête proprement tous les services (placeholder)
- [x] `aitao.sh status`: Affiche dashboard TUI (modules, config, directories)
- [x] `aitao.sh ingest <path>`: Ingestion manuelle (placeholder Sprint 1)
- [x] `aitao.sh search "query"`: Recherche en CLI (placeholder Sprint 2)
- [x] `aitao.sh logs <module>`: Affiche les logs (implémenté)
- [x] `aitao.sh config validate`: Valide config.yaml (implémenté)
- [x] `aitao.sh test`: Lance les tests unitaires

**Estimation:** 5 points  
**Dépendances:** US-001, US-002, US-003  
**Commit:** (en cours) - Date: 2026-01-28

**Note:** Version Sprint 0 avec foundation modules. Les commandes start/stop/ingest/search
sont des placeholders qui seront implémentées dans les sprints suivants.

---

### Epic 2: Base de données [MUST]

#### US-006: Intégrer LanceDB [MUST] ✅ DONE
**En tant que** système  
**Je veux** un index vectoriel local  
**Afin de** faire de la recherche sémantique

**Critères d'acceptation:**
- [x] Classe `LanceDBClient` dans `src/search/lancedb_client.py`
- [x] Connexion à LanceDB (`${storage_root}/lancedb`)
- [x] Schéma: id (sha256), path, title, content, embeddings, metadata
- [x] Méthodes: `add_document()`, `search()`, `delete()`, `get_stats()`
- [x] Embeddings avec `sentence-transformers/all-MiniLM-L6-v2`
- [x] Tests unitaires: 26 tests passent

**Estimation:** 5 points  
**Dépendances:** US-001, US-003  
**Commit:** `2afeb47` - Tag: v2.1.6 - Date: 2026-01-28

---

#### US-007: Intégrer Meilisearch [MUST] ✅ DONE
**En tant que** système  
**Je veux** un moteur de recherche full-text  
**Afin de** faire de la recherche rapide avec filtres

**Critères d'acceptation:**
- [x] Classe `MeilisearchClient` dans `src/search/meilisearch_client.py`
- [x] Connexion à Meilisearch host (`localhost:7700`)
- [x] Création index `aitao_documents` avec filtres: date, path, category, language
- [x] Méthodes: `add_document()`, `search()`, `delete()`, `get_stats()`
- [x] Gestion des erreurs (connexion, index missing)
- [x] Tests unitaires: 25 tests passent

**Estimation:** 5 points  
**Dépendances:** US-001, US-003  
**Commit:** `ab03007` - Tag: v2.1.7 - Date: 2026-01-28

---

#### US-007b: Refactoring CLI modulaire [MUST] ✅ DONE
**En tant que** développeur  
**Je veux** un CLI Python modulaire avec Typer  
**Afin de** faciliter la maintenance et l'extension

**Critères d'acceptation:**
- [x] Package `src/cli/` avec architecture modulaire
- [x] Framework Typer + Rich pour l'interface
- [x] Commandes: status, version, test
- [x] Groupe `ms`: status, start, stop, restart, upgrade, rebuild
- [x] Groupe `db`: status, stats, clear, search
- [x] Groupe `config`: show, validate, edit
- [x] Helpers Rich (spinners, tables, status lines)
- [x] Mode quiet par défaut (AITAO_QUIET), --debug pour verbose
- [x] Aide détaillée avec toutes les sous-commandes
- [x] `aitao.sh` simplifié (~45 lignes, façade bash)
- [x] Tests unitaires: 9 tests CLI

**Estimation:** 5 points  
**Dépendances:** US-006, US-007  
**Commit:** `1cc4cf2` - Tag: v2.1.8 - Date: 2026-01-28

---

## Sprint 1: Indexation basique (2 semaines - Fév 2026) ✅ COMPLETE

### Epic 3: Filesystem Scanning [MUST] ✅

#### US-008: Scanner filesystem [MUST] ✅ DONE
**En tant que** système  
**Je veux** scanner les volumes configurés  
**Afin de** détecter les nouveaux fichiers

**Critères d'acceptation:**
- [x] Classe `FilesystemScanner` dans `src/indexation/scanner.py`
- [x] Lit `config.yaml` → `indexing.include_paths`
- [x] Parcourt récursivement les volumes
- [x] Skip patterns: `.*`, `__pycache__`, `node_modules`, `.git`
- [x] Filtre par extensions supportées (28 types)
- [x] Compare mtime + SHA256 pour détecter modifications
- [x] Retourne liste de fichiers nouveaux/modifiés/supprimés
- [x] State persistence (scanner_state.json)
- [x] CLI: scan run, scan paths, scan status, scan clear
- [x] Tests unitaires: 22 tests passent

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager)  
**Commit:** `aaecffa` - Tag: v2.1.9 - Date: 2026-01-28

---

#### US-009: Créer système de queue [MUST] ✅ DONE
**En tant que** système  
**Je veux** une queue JSON pour les tâches d'indexation  
**Afin de** traiter les fichiers de manière asynchrone

**Critères d'acceptation:**
- [x] Classe `TaskQueue` dans `src/indexation/queue.py`
- [x] Fichier JSON: `${storage_root}/queue/tasks.json`
- [x] Structure: `[{id, file_path, task_type, priority, added_at, status}]`
- [x] Méthodes: `add_task()`, `get_next_task()`, `update_status()`, `get_stats()`
- [x] Priorités: `high`, `normal`, `low`
- [x] Statuts: `pending`, `processing`, `completed`, `failed`
- [x] Thread-safe (file locking avec fcntl)
- [x] CLI: queue status, queue list, queue add, queue clear, queue retry, queue cancel, queue info
- [x] Tests unitaires: 51 tests passent

**Estimation:** 3 points  
**Dépendances:** US-001 (PathManager)  
**Commit:** Tag: v2.1.10 - Date: 2026-01-28

---

#### US-010: Créer background worker [MUST] ✅ DONE
**En tant que** système  
**Je veux** un worker qui traite la queue  
**Afin de** indexer les fichiers en arrière-plan

**Critères d'acceptation:**
- [x] Classe `BackgroundWorker` dans `src/indexation/worker.py`
- [x] Boucle infinie: poll queue configurable (default: 30 secondes)
- [x] Traite les tâches séquentiellement (1 à la fois)
- [x] Vérifie charge système (CPU <80% configurable) avant traitement
- [x] Met à jour statut tâche: `pending` → `processing` → `completed`/`failed`
- [x] Daemon mode avec PID file (`/tmp/aitao_worker.pid`)
- [x] CLI: worker status, worker start, worker stop, worker restart, worker run-once, worker logs
- [x] Graceful shutdown (SIGTERM/SIGINT)
- [x] Tests unitaires: 40 tests passent

**Estimation:** 5 points  
**Dépendances:** US-009 (TaskQueue), US-002 (Logger)  
**Commit:** Tag: v2.1.11 - Date: 2026-01-28

---

### Epic 4: Indexation texte direct [MUST]

#### US-011: Extraire texte direct (PDF, DOCX) [MUST] ✅ DONE
**En tant que** système  
**Je veux** extraire le texte des documents  
**Afin de** les indexer sans OCR

**Critères d'acceptation:**
- [x] Classe `TextExtractor` dans `src/indexation/text_extractor.py`
- [x] PDF: `pypdf` avec extraction de métadonnées
- [x] DOCX: `python-docx` avec support des tableaux
- [x] TXT, MD, RST, TEX: lecture directe avec détection encodage
- [x] Code (.py, .js, .ts, etc.): 30+ extensions supportées
- [x] JSON: parsing et formatage
- [x] Retourne: `ExtractionResult{text, metadata: {pages, word_count, language}}`
- [x] Détecte langue (langdetect)
- [x] CLI: extract file, extract batch, extract types, extract test
- [x] Tests unitaires: 36 tests passent

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager)  
**Commit:** Tag: v2.2.11 - Date: 2026-01-28

---

#### US-012: Indexer documents dans LanceDB + Meilisearch [MUST] ✅ DONE
**En tant que** système  
**Je veux** indexer les documents extraits  
**Afin de** permettre la recherche

**Critères d'acceptation:**
- [x] Classe `DocumentIndexer` dans `src/indexation/indexer.py`
- [x] Workflow: Extract text → Generate embeddings → Index LanceDB + Meilisearch
- [x] Calcule SHA256 (déduplication)
- [x] Extrait metadata: path, mtime, size, language, category
- [x] Ajoute à LanceDB (embeddings)
- [x] Ajoute à Meilisearch (full-text + filtres)
- [x] Log succès/erreurs
- [x] CLI: index file, index batch, index status, index delete, index test
- [x] Tests unitaires: 33 tests passent

**Estimation:** 5 points  
**Dépendances:** US-006 (LanceDB), US-007 (Meilisearch), US-011 (TextExtractor)  
**Commit:** Tag: v2.2.12 - Date: 2026-01-28

---

#### US-012b: Dette technique - Gestion des dépendances uv [SHOULD] ✅ DONE
**En tant que** développeur  
**Je veux** que toutes les dépendances soient gérées via `uv`  
**Afin de** respecter le PRD et garantir la reproductibilité

**Contexte:**
Durant le développement, des confusions ont eu lieu entre `pip` et `uv`.
Le PRD stipule clairement: "uv-first: All Python dependencies managed via `uv` (not raw `pip`)".

**Critères d'acceptation:**
- [x] Vérifier que toutes les dépendances sont dans `pyproject.toml`
- [x] Script de validation `scripts/check_deps.py` 
- [x] Documenter la procédure d'installation avec `uv sync`
- [x] Ajouter un pre-commit hook ou CI check pour détecter `pip install`
- [x] README.md créé avec instructions uv

**Estimation:** 2 points  
**Dépendances:** Aucune  
**Commit:** Tag: v2.2.12b - Date: 2026-01-28

---

## Sprint 3: Recherche hybride (2 semaines - Mars 2026)

### Epic 5: Search API [MUST]

#### US-013: Créer API REST FastAPI [MUST] ✅ DONE
**En tant que** développeur  
**Je veux** une API REST pour accéder à AItao  
**Afin de** intégrer avec Continue/Wave/Custom UI

**Critères d'acceptation:**
- [x] FastAPI app dans `src/api/main.py`
- [x] Endpoints: `/api/search`, `/api/ingest`, `/api/health`, `/api/stats`
- [x] CORS configuré (`config.yaml` → `api.cors_origins`)
- [x] Port configurable (défaut: 5000)
- [x] Documentation OpenAPI auto-générée (`/docs`)
- [x] Logging des requêtes
- [x] Tests unitaires + intégration: 28 tests passent

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager), US-002 (Logger)  
**Commit:** Tag: v2.2.13 - Date: 2026-01-28

---

#### US-014: Implémenter recherche hybride [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** une recherche combinant full-text + sémantique  
**Afin de** trouver mes documents rapidement

**Critères d'acceptation:**
- [x] Endpoint `POST /api/search`
- [x] Requête parallèle: Meilisearch + LanceDB
- [x] Merge résultats (weighted: 40% Meilisearch, 60% LanceDB)
- [x] Filtres: date_after, date_before, path_contains, category, language
- [x] Retourne top 10 avec: path, title, summary, score, metadata
- [x] Classe `HybridSearchEngine` avec exécution parallèle
- [x] CLI: search run, search test, search modes
- [x] Tests unitaires: 32 tests passent

**Estimation:** 8 points  
**Dépendances:** US-006 (LanceDB), US-007 (Meilisearch), US-013 (API)
**Commit:** Tag: v2.2.14 - Date: 2026-01-28

---

#### US-015: Implémenter endpoint /api/health [MUST] ✅ DONE
**En tant que** système externe  
**Je veux** vérifier la santé d'AItao  
**Afin de** détecter les problèmes

**Critères d'acceptation:**
- [x] Endpoint `GET /api/health`
- [x] Vérifie: API running, LanceDB connected, Meilisearch connected
- [x] Retourne JSON: `{status, services: {api, lancedb, meilisearch, worker}, timestamp}`
- [x] Status: `healthy`, `degraded`, `down`
- [x] Tests unitaires (23 tests)

**Estimation:** 2 points  
**Dépendances:** US-013 (API)
**Version:** v2.2.15

---

## Sprint 3: RAG & LLM + Ollama (2 semaines - Fév 2026) 🚀

### Epic 5b: LLM Backend & RAG [MUST]

#### US-016: Créer OllamaClient [MUST] ✅ DONE
**En tant que** système  
**Je veux** un client pour interagir avec Ollama  
**Afin de** faire des inférences LLM avec les modèles disponibles

**Critères d'acceptation:**
- [x] Classe `OllamaClient` dans `src/llm/ollama_client.py`
- [x] Méthodes: `list_models()`, `chat()`, `generate()`, `embeddings()`
- [x] Connexion à Ollama (`config.yaml` → `llm.ollama.host`)
- [x] Gestion erreurs (Ollama not running, model not found)
- [x] Streaming support (SSE)
- [x] Tests unitaires (18 tests)

**Estimation:** 3 points  
**Dépendances:** US-003 (ConfigManager)  
**Commit:** Tag: v2.3.16 - Date: 2026-01-29

---

#### US-017: Créer RAGEngine [MUST] ✅ DONE
**En tant que** système  
**Je veux** enrichir les prompts avec du contexte documentaire  
**Afin de** fournir des réponses plus pertinentes au LLM

**Critères d'acceptation:**
- [x] Classe `RAGEngine` dans `src/llm/rag_engine.py`
- [x] Méthodes: `search_context()`, `enrich_prompt()`, `enrich_messages()`
- [x] Workflow: user prompt → search (LanceDB+Meilisearch) → enrich → return
- [x] Config: max_context_docs, context_max_tokens (`config.toml` section [rag])
- [x] Retourne: enriched_prompt, context_docs (pour affichage)
- [x] Tests unitaires (21 tests)

**Estimation:** 3 points  
**Dépendances:** US-014 (HybridSearch), US-016 (OllamaClient)  
**Commit:** Tag: v2.3.17 - Date: 2026-01-29

---

#### US-018: Endpoint /api/chat (RAG + Ollama) [MUST] ✅ DONE
**En tant que** utilisateur (via Continue.dev, AnythingLLM, etc.)  
**Je veux** un endpoint chat compatible Ollama et OpenAI  
**Afin de** parler avec le LLM enrichi par RAG

**Critères d'acceptation:**
- [x] Endpoint `POST /api/chat` (Ollama-compatible format)
- [x] Endpoint `POST /v1/chat/completions` (OpenAI-compatible format)
- [x] Requête: `{model, messages, stream, ...}`
- [x] Workflow: receive prompt → RAG enrichment → forward to Ollama → stream response
- [x] RAG context metadata in response (rag_context field)
- [x] Streaming SSE support
- [x] Tests unitaires (22 tests)

**Estimation:** 5 points  
**Dépendances:** US-016 (OllamaClient), US-017 (RAGEngine)  
**Commit:** Tag: v2.3.18 - Date: 2026-01-30

---

#### US-019: Configurer Continue.dev [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** que Continue.dev se connecte facilement à AItao  
**Afin de** utiliser le RAG dans mon IDE

**Critères d'acceptation:**
- [x] Documenter configuration Continue.dev (config.yaml et config.json)
- [x] Exemple: `apiBase: "http://localhost:5000/v1"` → appelle AItao
- [x] Créer guide d'installation (docs/CONTINUE_SETUP.md)
- [x] Vérifier modèles disponibles (via `/api/tags` et `/v1/models`)
- [x] Documentation troubleshooting et configuration avancée

**Estimation:** 2 points  
**Dépendances:** US-018 (/api/chat endpoint), US-020 (/api/tags)  
**Commit:** Tag: v2.3.19 - Date: 2026-01-29

---

#### US-020: Endpoint /api/models (liste modèles) [MUST] ✅ DONE
**En tant que** client externe  
**Je veux** découvrir les modèles disponibles  
**Afin de** choisir le modèle pour mon request

**Critères d'acceptation:**
- [x] Endpoint `GET /api/tags` (Ollama-compatible)
- [x] Endpoint `GET /v1/models` (OpenAI-compatible)
- [x] Endpoint `GET /api/show/{model}` (model details)
- [x] Endpoint `GET /v1/models/{model}` (OpenAI single model)
- [x] Retourne liste modèles de Ollama avec details
- [x] Format Ollama: `{models: [{name, size, digest, modified_at, details}]}`
- [x] Format OpenAI: `{object: "list", data: [{id, object, created, owned_by}]}`
- [x] Tests unitaires (13 tests)

**Estimation:** 2 points  
**Dépendances:** US-016 (OllamaClient)  
**Commit:** Tag: v2.3.19 - Date: 2026-01-29

---

#### US-021: CLI chat interactif [SHOULD] ✅ DONE
**En tant que** utilisateur  
**Je veux** discuter avec le LLM en CLI  
**Afin de** tester rapidement sans interface externe

**Critères d'acceptation:**
- [x] Commande: `python -m src.cli.chat` (ou `./aitao.sh chat`)
- [x] Interactive mode: user types → AItao searches RAG → LLM responds
- [x] Show context documents used (for debugging) - toggle with `/context on|off`
- [x] Multi-turn conversation (memory)
- [x] Save conversation to history file (`data/history/chat/`)
- [x] Commands: /quit, /clear, /context, /stats, /model, /history, /help
- [x] Streaming responses with color-coded output
- [x] Tests unitaires (16 tests)

**Estimation:** 3 points  
**Dépendances:** US-018 (/api/chat), US-017 (RAGEngine)  
**Commit:** Tag: v2.3.20 - Date: 2026-01-29

---

## 🔍 Sprint Q&A: Vérifications & Fixes (1 semaine - Jan 29 2026)

### QA-001: Vérifier CLI aitao.sh commands [MUST]
**Problème:** Commande `./aitao.sh stop` échoue avec "No such command 'stop'"  
**Contexte:** `stop` n'est qu'une sous-commande de `ms` (Meilisearch), pas une commande racine

**Résolution:**
- ✅ Diagnostic: Les commandes doivent être `ms stop`, `ms start`, pas `stop`, `start`
- ✅ **AMÉLIORATION:** Créé commandes `start`, `stop`, `restart` au niveau racine!
- ✅ Documentation mise à jour dans docs/CLI_USAGE.md
- ✅ Créé 15 tests pour les nouvelles commandes (tous passent!)

**Commandes correctes (AVANT):**
```bash
./aitao.sh ms stop     # Meilisearch uniquement
./aitao.sh ms start    # Meilisearch uniquement
```

**Commandes correctes (MAINTENANT - Plus simple!):**
```bash
./aitao.sh start       # 🌟 Démarre TOUS les services
./aitao.sh stop        # 🌟 Arrête TOUS les services  
./aitao.sh restart     # 🌟 Redémarre TOUS les services
```

**Fichiers créés/modifiés:**
- src/cli/commands/lifecycle.py (NEW - 207 lignes)
- tests/test_lifecycle_commands.py (NEW - 15 tests)
- src/cli/main.py (UPDATED - added start/stop/restart commands)
- docs/CLI_USAGE.md (UPDATED - new section for user-friendly commands)

**Estimation:** 2 points  
**Status:** ✅ COMPLÉTÉ

---

### QA-002: Vérifier config.yaml variable substitution [MUST]
**Problème (FIXÉ):** `${storage_root}` était créé littéralement au lieu d'être substitué

**Résolution:**
- ✅ Fix: `resolve_path()` dans `src/core/lib/path_manager.py` supporte now `${VAR}` syntax
- ✅ Fix: Section `system` renommée en `paths` dans `src/core/pathmanager.py`
- ✅ Cleanup: Suppression des fichiers mal nommés du git
- ✅ Commit: Commits a44fa78 + d99ea11

**Status:** ✅ Complété

---

### QA-003: Tests E2E Startup Chain + Fix Lifecycle [MUST] 🚨
**Problème CRITIQUE:** 476 tests unitaires passent mais l'application ne fonctionne pas!  
**Cause:** `./aitao.sh start` ne démarre que Meilisearch, pas le pipeline complet.

**Objectif:** Garantir que le système fonctionne de bout en bout.

**Critères d'acceptation:**

**1. Corriger lifecycle.py pour démarrer TOUS les services:**
- [ ] Meilisearch (brew services) ✅ déjà fait
- [ ] API FastAPI (port 5000)
- [ ] Worker daemon (background indexing)
- [ ] Initial scan trigger (populate queue)

**2. Créer tests E2E (Smoke Tests):**
- [ ] `tests/e2e/test_startup_chain.py`
- [ ] Test: `./aitao.sh start` → tous services running
- [ ] Test: Scan → Queue populated → Worker processes → Documents indexed
- [ ] Test: `./aitao.sh search "test"` → Retourne des résultats
- [ ] Test: `./aitao.sh stop` → Tous services arrêtés proprement

**3. Mettre à jour la Définition de "Done":**
- [ ] Ajouter: "Test E2E prouve que la fonctionnalité est accessible à l'utilisateur final"
- [ ] Ajouter: "Validation manuelle du workflow complet avant clôture de sprint"

**Workflow attendu après fix:**
```bash
./aitao.sh start
    ↓
1. Meilisearch starts (brew services)
2. API FastAPI starts (port 5000)
3. Worker daemon starts (background)
4. Initial scan runs (add files to queue)
5. Worker processes queue (indexing with progress)
```

**Estimation:** 5 points  
**Dépendances:** QA-001, QA-002  
**Status:** ✅ COMPLÉTÉ  
**Version:** 2.3.21.3

---

### QA-004: Documentation help CLI [SHOULD] ✅ DONE
**Contexte:** L'aide CLI affiche des commandes complètes

**Résolution:**
- ✅ README.md entièrement réécrit pour utilisateur non-technique
- ✅ Explications: Pourquoi AItao (gratuit, privé, écologique)
- ✅ Installation étape par étape complète
- ✅ Toutes les commandes CLI documentées avec exemples
- ✅ Endpoints API pour Continue, AnythingLLM, Open WebUI
- ✅ Troubleshooting section
- ✅ Types de fichiers supportés

**Fichiers modifiés:**
- README.md (RÉÉCRIT - ~400 lignes orientées utilisateur)

**Estimation:** 2 points  
**Status:** ✅ COMPLÉTÉ  
**Version:** 2.3.21.4

---

### QA-005: Vérifier structure fichiers config [SHOULD] ✅ DONE
**Context:** Vérifier que config.yaml est bien structuré et documenté

**Résolution:**
- ✅ Sections présentes: `paths`, `worker`, `indexing`, `ocr`, `api`, `logging` etc.
- ✅ Variables d'environnement: `${HOME}`, `${storage_root}` fonctionnent
- ✅ Fichier `config.yaml.template` créé pour installation propre
- ✅ Documentation inline (commentaires YAML)

**Fichiers créés:**
- config/config.yaml.template (NEW - ~230 lignes)

**Estimation:** 1 point  
**Status:** ✅ COMPLÉTÉ  
**Version:** 2.3.21.5

---

### QA-006: Nettoyage Legacy V1 [MUST] ✅ DONE 🧹
**Problème:** Du code legacy de la V1 pollue le workspace et cause des confusions.

**Objectif:** Identifier et supprimer TOUT ce qui n'est pas défini dans le PRD/Backlog.

**Résolution:**
- ✅ `src/core/sync_agent.py` - N'existe plus (déjà supprimé)
- ✅ `src/core/server.py` - N'existe plus (déjà supprimé)
- ✅ Références au port 18000 - Uniquement dans fichiers externes (.continue), pas dans projet
- ✅ Lien symbolique `config/aitao-nginx.conf` legacy supprimé
- ✅ Modules stubs préparés pour Sprint 4-7 (ocr, translation, dashboard)
- ✅ Aucun import orphelin trouvé
- ✅ 486 tests passent après nettoyage

**Fichiers supprimés:**
- config/aitao-nginx.conf (lien symbolique vers config V1)

**Estimation:** 3 points  
**Status:** ✅ COMPLÉTÉ  
**Version:** 2.3.21.5

---

**Sprint Q&A Résumé:**
- ✅ QA-001: Commandes start/stop/restart ajoutées
- ✅ QA-002: Variables config.yaml corrigées
- ✅ QA-003: Tests E2E + Fix lifecycle (CRITIQUE)
- ✅ QA-004: Documentation utilisateur README.md
- ✅ QA-005: config.yaml.template créé
- ✅ QA-006: Nettoyage legacy V1 terminé

**🎉 Sprint Q&A COMPLÉTÉ - 486 tests passent**

**🎉 Sprint Q&A COMPLÉTÉ - 486 tests passent**

---

## Sprint 4: OCR & Extraction (3 semaines - Mar-Apr 2026)

### Epic 6: OCR Pipeline [MUST]

#### US-022: Détecter tableaux dans PDF/images [SHOULD] 📋
**En tant que** système  
**Je veux** détecter la présence de tableaux  
**Afin de** router vers le bon OCR

**Critères d'acceptation:**
- [ ] Classe `TableDetector` dans `src/ocr/table_detector.py`
- [ ] Utilise OpenCV pour détecter contours
- [ ] Calcule score de probabilité (seuil configurable: 0.7)
- [ ] Retourne: `{has_tables: bool, confidence: float}`
- [ ] Tests avec images de test (tableaux, texte simple)

**Estimation:** 3 points  
**Dépendances:** Aucune

---

#### US-023: Intégrer AppleScript OCR [MUST] 📋
**En tant que** système  
**Je veux** utiliser l'OCR natif macOS  
**Afin d'** OCRer rapidement les documents simples

**Critères d'acceptation:**
- [ ] Classe `AppleScriptOCR` dans `src/ocr/applescript_ocr.py`
- [ ] Appel AppleScript via subprocess
- [ ] Entrée: chemin PDF/image
- [ ] Sortie: texte extrait
- [ ] Gestion erreurs (OCR failed)
- [ ] Cache résultats (`${storage_root}/cache/ocr/{sha256}.json`)
- [ ] Tests avec documents de test

**Estimation:** 3 points  
**Dépendances:** US-001 (PathManager)

---

#### US-024: Intégrer Qwen-VL OCR [MUST] 🔄
**En tant que** système  
**Je veux** utiliser Qwen-VL pour les documents complexes  
**Afin d'** extraire texte + tableaux avec précision

**Critères d'acceptation:**
- [ ] Classe `QwenVLOCR` dans `src/ocr/qwen_vl_ocr.py`
- [ ] Charge modèle + mmproj (`config.yaml` → `ocr.qwen_vl`)
- [ ] Entrée: chemin PDF/image + `extract_tables=True/False`
- [ ] Sortie: `{text, tables: [{table_id, data: [...]}]}`
- [ ] Format tables: JSON (défaut), CSV, Markdown
- [ ] Cache résultats
- [ ] Tests avec documents de test (tableaux)

**Estimation:** 5 points  
**Dépendances:** US-001 (PathManager), US-003 (ConfigManager)  
**Note:** Script bench déjà existant, à intégrer

---

#### US-025: Créer OCR Router [MUST] 📋
**En tant que** système  
**Je veux** un router qui choisit le bon OCR  
**Afin d'** optimiser vitesse/qualité

**Critères d'acceptation:**
- [ ] Classe `OCRRouter` dans `src/ocr/router.py`
- [ ] Workflow:
  1. Essayer extraction texte direct (pdfminer)
  2. Si insuffisant, détecter tableaux
  3. Si tableaux → Qwen-VL, sinon AppleScript OCR
- [ ] Configurable (`config.yaml` → `ocr.router`)
- [ ] Retourne: `{method, text, tables, metadata}`
- [ ] Tests avec divers documents

**Estimation:** 5 points  
**Dépendances:** US-022, US-023, US-024

---

### Epic 7: Extraction EXIF [SHOULD]

#### US-026: Extraire métadonnées EXIF des images [SHOULD] 📋
**En tant que** système  
**Je veux** extraire les EXIF des images  
**Afin d'** enrichir l'indexation

**Critères d'acceptation:**
- [ ] Classe `EXIFExtractor` dans `src/indexation/exif_extractor.py`
- [ ] Extraction: date_taken, camera, location (GPS), dimensions
- [ ] Retourne: `{exif: {...}, metadata: {...}}`
- [ ] Indexe dans LanceDB + Meilisearch (filtres)
- [ ] Tests avec images de test (avec/sans EXIF)

**Estimation:** 3 points  
**Dépendances:** US-012 (DocumentIndexer)

---

## Sprint 5: Traduction (2 semaines - Avr-Mai 2026)

### Epic 8: Translation Pipeline [MUST]

#### US-027: Créer pipeline de traduction [MUST] 📋
**En tant que** utilisateur  
**Je veux** traduire des documents chinois  
**Afin de** les comprendre en français/anglais

**Critères d'acceptation:**
- [ ] Classe `Translator` dans `src/translation/translator.py`
- [ ] LLM: Qwen-2.5-Coder ou équivalent (`config.yaml` → `translation.model`)
- [ ] Entrée: texte chinois
- [ ] Sortie: `{translation_fr, translation_en, confidence}`
- [ ] Prompt engineering pour contexte formel
- [ ] Cache traductions (`${storage_root}/cache/translations/{sha256}.json`)
- [ ] Tests avec documents de test

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager)

---

#### US-028: Extraire actions/deadlines [MUST] 📋
**En tant que** utilisateur  
**Je veux** extraire les échéances d'un document  
**Afin de** connaître mes tâches et deadlines

**Critères d'acceptation:**
- [ ] Classe `ActionExtractor` dans `src/translation/action_extractor.py`
- [ ] Prompt LLM pour extraire: deadlines, tasks, amounts, entities
- [ ] Retourne JSON: `{deadlines: [{task, date, days_remaining}], actions, entities}`
- [ ] Parse dates (français, anglais, chinois)
- [ ] Calcule days_remaining
- [ ] Tests avec documents de test

**Estimation:** 5 points  
**Dépendances:** US-021 (Translator)

---

#### US-029: API endpoint /api/translate [MUST] 📋
**En tant que** utilisateur  
**Je veux** traduire un document via API  
**Afin de** l'intégrer dans mon workflow

**Critères d'acceptation:**
- [ ] Endpoint `POST /api/translate`
- [ ] Entrée: `{file_path OR text, source_lang, target_lang, extract_actions}`
- [ ] Workflow: OCR (si nécessaire) → Translate → Extract actions
- [ ] Retourne: `{translation, actions, metadata}`
- [ ] Tests unitaires + intégration

**Estimation:** 3 points  
**Dépendances:** US-027, US-028, US-013 (API)

---

## Sprint 6: Catégorisation (2 semaines - Mai 2026)

### Epic 9: Category Management [SHOULD]

#### US-030: Auto-catégoriser documents [SHOULD] 📋
**En tant que** système  
**Je veux** catégoriser automatiquement les documents  
**Afin de** faciliter la recherche

**Critères d'acceptation:**
- [ ] Classe `Categorizer` dans `src/indexation/categorizer.py`
- [ ] Charge catégories depuis `config/categories.yaml`
- [ ] LLM analyse: title + first 1000 words + keywords
- [ ] Retourne: `{category, confidence}`
- [ ] Si confidence <0.7 → flag pour review manuel
- [ ] Tests avec documents de test

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager)

---

#### US-031: API correction catégories [SHOULD] 📋
**En tant que** utilisateur  
**Je veux** corriger les catégories erronées  
**Afin d'** améliorer le système

**Critères d'acceptation:**
- [ ] Endpoint `PUT /api/categories/{doc_id}`
- [ ] Entrée: `{new_category, reason}`
- [ ] Met à jour metadata dans LanceDB + Meilisearch
- [ ] Sauvegarde correction dans `corrections.json`
- [ ] Retourne: `{success, message}`
- [ ] Tests unitaires

**Estimation:** 3 points  
**Dépendances:** US-013 (API), US-030 (Categorizer)

---

#### US-032: Feedback loop catégorisation [COULD] 🔮
**En tant que** système  
**Je veux** utiliser les corrections pour améliorer  
**Afin d'** augmenter la précision

**Critères d'acceptation:**
- [ ] Lit `corrections.json`
- [ ] Ajuste prompt système avec exemples de corrections
- [ ] Option: Fine-tuning model (V3+)
- [ ] Tests avec corrections simulées

**Estimation:** 5 points  
**Dépendances:** US-031  
**Note:** Nice-to-have, peut être déféré

---

## Sprint 7: Dashboard & Polish (2 semaines - Juin 2026)

### Epic 10: CLI & Dashboard [SHOULD]

#### US-033: Dashboard TUI (status) [SHOULD] 📋
**En tant que** utilisateur  
**Je veux** voir le statut d'AItao en CLI  
**Afin de** monitorer le système

**Critères d'acceptation:**
- [ ] Script `src/dashboard/tui.py`
- [ ] Utilise Rich (Python TUI)
- [ ] Affiche: Services (API, Worker, LanceDB, Meilisearch), Resources (CPU, RAM, Disk), Recent Activity
- [ ] Refresh auto toutes les 5 secondes
- [ ] Couleurs: vert (OK), jaune (warning), rouge (erreur)
- [ ] Accessible via `./aitao.sh status`

**Estimation:** 5 points  
**Dépendances:** US-005 (CLI)

---

#### US-034: Cronjob daily scan [MUST] 📋
**En tant que** système  
**Je veux** scanner les volumes quotidiennement  
**Afin d'** indexer les nouveaux fichiers

**Critères d'acceptation:**
- [ ] Script `scripts/daily_scan.sh`
- [ ] Cron: `0 2 * * *` (2am daily)
- [ ] Appelle `FilesystemScanner` → ajoute à queue
- [ ] Log début/fin scan (JSON)
- [ ] Notification utilisateur: "X nouveaux documents détectés"
- [ ] Tests avec cronjob simulé

**Estimation:** 2 points  
**Dépendances:** US-008 (FilesystemScanner), US-009 (TaskQueue)

---

#### US-035: System load monitor [SHOULD] 📋
**En tant que** système  
**Je veux** détecter la charge système  
**Afin de** throttler les tâches background

**Critères d'acceptation:**
- [ ] Classe `SystemMonitor` dans `src/core/system_monitor.py`
- [ ] Méthodes: `get_cpu_percent()`, `get_memory_usage()`, `get_disk_usage()`
- [ ] Détecte activité utilisateur (macOS: mouse/keyboard events)
- [ ] Retourne: `{is_busy: bool, cpu_percent, memory_gb, disk_gb}`
- [ ] Worker utilise ce module pour throttler
- [ ] Tests unitaires

**Estimation:** 3 points  
**Dépendances:** US-010 (Worker)

---

### Epic 11: Testing & Documentation [SHOULD]

#### US-036: Tests end-to-end [SHOULD] 📋
**En tant que** développeur  
**Je veux** des tests E2E  
**Afin de** garantir le fonctionnement

**Critères d'acceptation:**
- [ ] Tests E2E dans `tests/e2e/`
- [ ] Scénarios: Ingest document → Index → Search → Retrieve
- [ ] Tests avec dataset réel (PDF, DOCX, images)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Coverage >80%

**Estimation:** 8 points  
**Dépendances:** Tous les précédents

---

#### US-037: Documentation utilisateur [SHOULD] 📋
**En tant que** utilisateur  
**Je veux** une documentation claire  
**Afin d'** installer et utiliser AItao

**Critères d'acceptation:**
- [ ] README.md mis à jour (v2)
- [ ] Installation guide (macOS)
- [ ] Configuration guide (config.yaml)
- [ ] API documentation (OpenAPI)
- [ ] Troubleshooting guide
- [ ] FAQ

**Estimation:** 5 points  
**Dépendances:** US-036

---

## Backlog (Future - V3+)

### Epic 12: Multi-platform [WON'T - V3]

- **US-032:** Support Linux
- **US-033:** Support Windows
- **US-034:** Docker full stack

### Epic 13: Advanced Features [WON'T - V3]

- **US-035:** Email indexing (Gmail, Outlook)
- **US-036:** Audio/Video transcription
- **US-037:** Image generation (local)
- **US-038:** Encryption at-rest
- **US-039:** Multi-user support

---

## Définition de "Done"

Une US est considérée "Done" quand:
1. ✅ Code écrit et respecte les conventions (< 400 lignes/fichier)
2. ✅ File header présent (description module)
3. ✅ Tests unitaires écrits et passent
4. ✅ Code review OK
5. ✅ Documentation inline (docstrings)
6. ✅ Logs JSON pour debugging
7. ✅ Intégré dans branche `pdr/v2-remodular`
8. 🚨 **Test E2E prouve que la fonctionnalité est accessible à l'utilisateur final**
9. 🚨 **Validation manuelle du workflow complet avant clôture de sprint**

### ⚠️ Leçon Apprise (QA-003):
> 476 tests unitaires ont passé pendant que l'application ne fonctionnait pas.
> Les tests unitaires testent les composants ISOLÉS.
> Les tests E2E testent l'EXPÉRIENCE UTILISATEUR RÉELLE.
> **Un composant qui fonctionne seul mais n'est pas câblé = fonctionnalité inexistante.**

---

## Points d'estimation

- **1 point:** 1-2 heures (trivial)
- **2 points:** 3-4 heures (simple)
- **3 points:** 1 jour (moyen)
- **5 points:** 2-3 jours (complexe)
- **8 points:** 4-5 jours (très complexe, à décomposer)

---

## Priorités MOSCOW

- **MUST:** Fonctionnalité critique pour MVP
- **SHOULD:** Importante mais pas bloquante
- **COULD:** Nice-to-have, peut être déférée
- **WON'T:** Hors scope V2, pour V3+

---

**Velocity cible:** 20-25 points/sprint (1 dev, 2 semaines)

**Total points MVP (Sprint 0-6):** ~140 points → 6-7 sprints → 3-4 mois
