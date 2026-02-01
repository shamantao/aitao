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
| **Sprint 3b: Model Management** | 📋 **PRIORITAIRE** | US-021b → US-021f | - | v2.3.22.x |
| **Sprint 3c: Virtual Models** | 📋 Pending | US-021g → US-021i | - | v2.3.23.x |
| Sprint Q&A: Vérifications | ✅ Complete | QA-001 → QA-006 | - | v2.3.21.x |
| Sprint 4: OCR & Extraction | 📋 Pending | US-022 → US-026 | - | v2.4.x |
| Sprint 5: Traduction | 📋 Pending | US-027 → US-029b | - | v2.5.x |
| Sprint 6: Catégorisation | 📋 Pending | US-030 → US-032b | - | v2.6.x |
| Sprint 7: Dashboard & Polish | 📋 Pending | US-033 → US-037b | - | v2.7.x |

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

### Epic 5c: Model Lifecycle Management [MUST] 🆕

**Contexte:** Les modèles LLM doivent être gérés automatiquement par AItao. L'utilisateur configure la liste dans `config.yaml`, AItao s'occupe du téléchargement et de la vérification.

**Priorité:** MUST - Bloque le fonctionnement du projet si les modèles ne sont pas présents.

#### US-021b: ModelManager - Vérification des modèles au démarrage [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** que AItao vérifie automatiquement la présence des modèles requis  
**Afin de** ne jamais avoir d'erreur "model not found" en pleine utilisation

**Intention:** Au démarrage, AItao doit s'assurer que tous les modèles configurés sont disponibles dans Ollama.

**Critères d'acceptation:**
- [x] Classe `ModelManager` dans `src/llm/model_manager.py`
- [x] Méthode `check_models() -> ModelStatus`:
  - Liste modèles dans `config.yaml` → `llm.models`
  - Compare avec `ollama list`
  - Retourne: `{present: [...], missing: [...], extra: [...]}`
- [x] Intégré dans `lifecycle.py` au démarrage (après Ollama, avant API)
- [x] Si modèle `required: true` manquant → erreur claire avec instructions
- [x] CLI: `./aitao.sh models status` affiche l'état des modèles
- [x] Tests unitaires

**Validation (obligatoire):**
- [x] Tests unitaires de la fonctionnalité (fichiers dédiés si nécessaire)
- [x] Tous les tests unitaires: `./aitao.sh validate`
- [x] Tests E2E: `./aitao.sh validate`
- [x] Validation fonctionnelle user-centric: `./aitao.sh validate`
- [x] Conformité PRD (modularité, docstrings EN, registry à jour, PathManager + logger utilisés)
- [x] Version bump conforme au plan: `2.${SPRINT}.${US}.${CORRECTIF}`
- [x] Commit + push GitHub effectués
- [x] Backlog mis à jour: US marquée ✅ DONE + validation renseignée

**Estimation:** 3 points  
**Dépendances:** US-016 (OllamaClient), US-003 (ConfigManager)

---

#### US-021c: ModelManager - Téléchargement automatique [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** que AItao télécharge automatiquement les modèles manquants  
**Afin de** ne jamais avoir à taper `ollama pull` manuellement

**Intention:** Expérience "out of the box" - l'utilisateur configure, AItao fait le reste.

**Critères d'acceptation:**
- [x] Méthode `pull_missing_models()` dans `ModelManager`
- [x] Utilise `ollama pull <model>` avec affichage progression
- [x] Timeout configurable (`config.yaml` → `llm.startup.pull_timeout_minutes`)
- [x] Option `--skip-pull` pour démarrage rapide sans téléchargement
- [x] CLI: `./aitao.sh models pull` force le téléchargement
- [x] Gestion erreurs: timeout, espace disque, network
- [x] Tests unitaires (avec mock ollama)

**Validation (effectuée):**
- [x] Tests unitaires: 8 tests + 427 total passing
- [x] Conformité PRD: docstrings EN, logging, ConfigManager utilisé
- [x] Version bump: 2.3.21.3
- [x] Commit: 458f2da

**Estimation:** 3 points ✅  
**Dépendances:** US-021b ✅  
**version finale:** 2.3.21.3 ✅

---

#### US-021d: Config.yaml - Structure modèles enrichie [MUST] ✅ DONE
**En tant que** utilisateur  
**Je veux** configurer mes modèles de façon déclarative  
**Afin de** contrôler précisément quels modèles sont utilisés

**Intention:** La configuration est la source de vérité pour les modèles.

**Critères d'acceptation:**
- [x] Nouvelle structure dans `config.yaml`:
  ```yaml
  llm:
    models:
      - name: "llama3.1:8b"
        required: true      # Bloque démarrage si absent
        size_gb: 4.7        # Info pour l'utilisateur
        roles: ["chat", "rag"]  # Usage prévu
      - name: "qwen2.5-coder:7b"
        required: false
        roles: ["code"]
  ```
- [x] Validation schema au chargement config
- [x] Migration automatique de l'ancien format (juste liste de noms)
- [x] Tests de parsing + validation

**Validation (effectuée):**
- [x] Tests unitaires: 26 tests dédiés + 453 total
- [x] Conformité PRD: docstrings EN, logging, ConfigManager utilisé
- [x] Version bump: 2.3.21.4
- [x] Commit: d1b49ab

**Fichiers modifiés:**
- `src/core/model_config.py`: Nouveau module de validation
- `src/llm/model_manager.py`: Intégration validate_model_config()
- `tests/unit/test_model_config.py`: 26 tests complets

**Fonctionnalités:**
- ModelConfigValidator pour validation/migration de schéma
- ModelConfigItem dataclass avec validation
- Support format ancien (backward compatible) ET nouveau
- Migration automatique lors du chargement
- Erreurs claires avec noms de champs
- Defaults pour champs optionnels

**Estimation:** 2 points ✅  
**Dépendances:** US-003 (ConfigManager) ✅  
**version finale:** 2.3.21.4 ✅  
**Commit:** d1b49ab ✅

---

#### US-021e: CLI models subcommand [SHOULD] ✅ DONE
**En tant que** utilisateur  
**Je veux** des commandes CLI pour gérer mes modèles  
**Afin de** voir l'état et agir manuellement si besoin

**Intention:** Transparence et contrôle pour l'utilisateur avancé.

**Critères d'acceptation:**
- [x] Groupe de commandes `./aitao.sh models`:
  - `status` - Liste modèles config vs installés ✅
  - `pull` - Télécharge les modèles manquants ✅ 
  - `add <name>` - Ajoute un modèle à la config + pull ✅
  - `remove <name>` - Retire de la config (propose suppression Ollama) ✅
- [x] Affichage Rich avec tableau coloré ✅
- [x] Confirmation avant toute suppression ✅
- [x] Tests unitaires ✅ (453 passed)

**Validation (obligatoire):**
- [x] Tests unitaires de la fonctionnalité (fichiers dédiés si nécessaire) ✅
- [x] Tous les tests unitaires: `./aitao.sh validate` ✅ 453 passed
- [x] Tests E2E: `./aitao.sh validate` ✅
- [x] Validation fonctionnelle user-centric: `./aitao.sh validate` ✅
- [x] Conformité PRD (modularité, docstrings EN, registry à jour, PathManager + logger utilisés) ✅
- [x] Version bump conforme au plan: `2.3.21.5`
- [ ] Commit + push GitHub effectués
- [x] Backlog mis à jour: US marquée ✅ DONE + validation renseignée

**Fichiers implémentés:**
- `src/cli/commands/models.py` - Commandes add() et remove()
- `src/cli/commands/_models_helpers.py` - Helpers: validate_model_name, load/save_config_yaml
- `src/llm/ollama_client.py` - Ajout de delete_model()

**Estimation:** 3 points ✅  
**Dépendances:** US-021b, US-021c ✅  
**Version finale:** 2.3.21.5 ✅

---

#### US-021f: Documentation migration GGUF → Ollama [SHOULD] ✅ DONE
**En tant que** utilisateur existant  
**Je veux** comprendre pourquoi mes GGUF locaux ne sont plus nécessaires  
**Afin de** libérer de l'espace disque et éviter la confusion

**Intention:** Clarifier la transition et éviter la duplication de stockage.

**Critères d'acceptation:**
- [x] Section dans README.md expliquant:
  - Les modèles Ollama sont gérés automatiquement
  - Les GGUF locaux (`models_dir`) ne sont plus nécessaires pour les modèles standard
  - Comment migrer (supprimer les GGUF après vérification)
  - Exception: modèles custom/fine-tuned restent en GGUF
- [x] Guide de migration dans `docs/MIGRATION_MODELS.md`
- [x] Mise à jour `config.yaml.template`

**Validation (obligatoire):**
- [x] Documentation mise à jour (README + guide migration)
- [x] Tous les tests unitaires: `./aitao.sh validate`
- [x] Tests E2E: `./aitao.sh validate`
- [x] Validation fonctionnelle user-centric: `./aitao.sh validate`
- [x] Conformité PRD (doc en anglais, cohérence config)
- [x] Version bump conforme au plan: `2.${SPRINT}.${US}.${CORRECTIF}`
- [x] Commit + push GitHub effectués
- [x] Backlog mis à jour: US marquée ✅ DONE + validation renseignée

**Estimation:** 1 point  
**Dépendances:** Aucune
**Version finale:** 2.3.21.6 ✅

---

## Sprint 3c: Virtual Models (1 semaine - Fév 2026)

**Architecture:** Modèles virtuels permettant à l'utilisateur de choisir le mode RAG via le nom du modèle.  
**Principe:** L'utilisateur garde le contrôle sur le niveau de contexte injecté, sans configuration complexe.

```
Noms des modèles virtuels:
├── *-basic      → RAG désactivé (code pur)
├── *-context    → RAG filtré par catégorie
├── *-doc        → RAG complet (tous les documents)
└── *-smart      → L'IA décide automatiquement (Sprint 7+)
```

### Epic 4b: Virtual Model Routing [MUST]

#### US-021g: Implémenter le routage des modèles virtuels [MUST] ✅ DONE
**En tant que** utilisateur de Continue.dev ou autre client  
**Je veux** choisir mon niveau de RAG via le nom du modèle  
**Afin de** ne pas avoir à modifier la configuration selon le contexte

**Intention:** Permettre le choix du mode RAG de façon transparente via le nom du modèle.

**Modèles virtuels proposés:**
| Modèle Virtuel | Comportement | Modèle Réel |
|----------------|--------------|-------------|
| `llama3.1-basic` | Code pur - pas de RAG | llama3.1-local:latest |
| `qwen-coder-basic` | Aide code - pas de RAG | qwen2.5-coder-local:latest |
| `qwen-coder-context` | Code + RAG catégorie "code" | qwen2.5-coder-local:latest |
| `llama3.1-doc` | RAG complet (documents) | llama3.1-local:latest |
| `llama3.1-smart` | L'IA décide (Sprint 7+) | llama3.1-local:latest |

**Critères d'acceptation:**
- [x] Parser le suffixe du modèle dans `src/api/routes/chat.py`
- [x] Mapper vers le modèle réel Ollama
- [x] Configurer le mode RAG selon le suffixe:
  - `-basic` → `rag_enabled = False`
  - `-context` → `rag_enabled = True, filter_category = "code"`
  - `-doc` → `rag_enabled = True, filter_category = None`
  - `-smart` → `rag_enabled = "auto"` (détection automatique - Sprint 7)
- [x] `/v1/models` expose les modèles virtuels aux clients
- [x] Tests unitaires pour chaque mode (30 tests)

**Estimation:** 5 points  
**Dépendances:** US-021b (OllamaClient), US-016 (RAG Engine)

**Validation (obligatoire):**
- [x] Tests unitaires: 30 tests pour virtual_models.py
- [x] Tous les tests unitaires passent: 483/483
- [x] Conformité PRD (doc en anglais, code cohérent)
- [x] Backlog mis à jour: US marquée ✅ DONE

**Version finale:** 2.3.21.7 ✅

---

#### US-021h: Configuration virtual_models dans config.yaml [SHOULD] 📋
**En tant que** administrateur  
**Je veux** configurer les modèles virtuels dans config.yaml  
**Afin de** personnaliser les noms et les mappings

**Critères d'acceptation:**
- [ ] Nouvelle section `virtual_models` dans config.yaml
- [ ] Définition des suffixes et comportements
- [ ] Possibilité de définir des filtres de catégorie personnalisés
- [ ] Documentation inline complète

**Exemple config.yaml:**
```yaml
virtual_models:
  enabled: true
  suffixes:
    basic:
      rag_enabled: false
    context:
      rag_enabled: true
      filter_categories: ["code", "config"]
    doc:
      rag_enabled: true
      filter_categories: null  # All categories
    smart:
      rag_enabled: auto
  mappings:
    llama3.1-basic: llama3.1-local:latest
    qwen-coder-basic: qwen2.5-coder-local:latest
    qwen-coder-context: qwen2.5-coder-local:latest
    llama3.1-doc: llama3.1-local:latest
```

**Estimation:** 3 points  
**Dépendances:** US-021g

---

#### US-021i: Test E2E Virtual Models [MUST] 📋
**En tant que** développeur  
**Je veux** un test complet du routage des modèles virtuels  
**Afin de** garantir que chaque mode fonctionne correctement

**Critères d'acceptation:**
- [ ] Test `qwen-coder-basic` → pas de contexte RAG injecté
- [ ] Test `qwen-coder-context` → contexte filtré catégorie "code"
- [ ] Test `llama3.1-doc` → contexte RAG complet
- [ ] Test modèle inconnu → erreur 404 ou fallback
- [ ] Intégré dans CI

**Estimation:** 3 points  
**Dépendances:** US-021g, US-021h

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

### QA-003: Tests E2E Startup Chain + Fix Lifecycle [MUST] ✅ DONE 🚨
**Problème CRITIQUE:** 476 tests unitaires passent mais l'application ne fonctionne pas!  
**Cause:** `./aitao.sh start` ne démarre que Meilisearch, pas le pipeline complet.

**Objectif:** Garantir que le système fonctionne de bout en bout.

**Résolution:**
- ✅ lifecycle.py corrigé pour démarrer TOUS les services
- ✅ Meilisearch (brew services)
- ✅ API FastAPI (port configurable, défaut 8200)
- ✅ Worker daemon (background indexing)
- ✅ Initial scan trigger (populate queue)
- ✅ Tests E2E créés: `tests/e2e/test_startup_chain.py` (10 tests)
- ✅ Définition de "Done" mise à jour avec critères E2E

**Fichiers créés/modifiés:**
- src/cli/commands/lifecycle.py (540 lignes)
- tests/e2e/test_startup_chain.py (10 tests E2E)

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

---

## Sprint 4: OCR & Extraction (3 semaines - Mar-Apr 2026)

**Architecture:** Pipeline OCR modulaire et multi-plateforme.  
**Principe:** Le Router définit l'interface, les Providers implémentent selon la plateforme.

```
src/ocr/
├── interfaces.py          # OCRProvider (abstract), OCRResult (dataclass)
├── router.py              # OCRRouter - sélection intelligente du provider
├── table_detector.py      # Détection de tableaux (OpenCV)
├── providers/
│   ├── native_provider.py # macOS: AppleScript / Linux: Tesseract
│   └── qwen_vl_provider.py
```

### Epic 6: OCR Pipeline [MUST]

#### US-022: OCR Router + Interfaces [MUST] 📋
**En tant que** développeur  
**Je veux** une architecture OCR modulaire avec interfaces claires  
**Afin de** pouvoir remplacer n'importe quel provider sans casser le système

**Intention:** Définir le contrat avant l'implémentation. Tout provider OCR doit respecter la même interface.

**Critères d'acceptation:**
- [ ] Interface abstraite `OCRProvider` dans `src/ocr/interfaces.py`
  - Méthode: `extract(path: Path) -> OCRResult`
  - Propriété: `name: str`, `platforms: list[str]`
- [ ] Dataclass `OCRResult` dans `src/ocr/interfaces.py`
  - Champs: `text, tables, method, confidence, metadata, error`
- [ ] Classe `OCRRouter` dans `src/ocr/router.py`
  - Détecte plateforme (macOS/Linux/Windows)
  - Sélectionne le provider approprié
  - Workflow: direct extraction → fallback OCR
- [ ] Config `config.yaml` → `ocr.default_provider`, `ocr.providers`
- [ ] Tests: mock providers pour valider le routing

**Estimation:** 5 points  
**Dépendances:** US-001 (PathManager), US-003 (ConfigManager)

---

#### US-023: Table Detector [SHOULD] 📋
**En tant que** système  
**Je veux** détecter la présence de tableaux dans les documents  
**Afin de** router vers Qwen-VL quand nécessaire

**Intention:** Optimiser le pipeline - les tableaux nécessitent un VLM, le texte simple peut utiliser l'OCR natif rapide.

**Critères d'acceptation:**
- [ ] Classe `TableDetector` dans `src/ocr/table_detector.py`
- [ ] Utilise OpenCV pour détecter contours structurés
- [ ] Seuil configurable (`config.yaml` → `ocr.table_detection_threshold`: 0.7)
- [ ] Retourne: `TableDetectionResult(has_tables: bool, confidence: float, regions: list)`
- [ ] Tests avec images de test (tableaux complexes, texte simple, mixte)

**Estimation:** 3 points  
**Dépendances:** US-022 (interfaces)

---

#### US-024: Native OCR Provider (macOS/Linux) [MUST] 📋
**En tant que** système  
**Je veux** un provider OCR natif multi-plateforme  
**Afin d'** OCRer rapidement les documents simples sur toute plateforme

**Intention:** Abstraction de l'OCR natif. macOS = AppleScript, Linux = Tesseract. Même interface, implémentation différente.

**Critères d'acceptation:**
- [ ] Classe `NativeOCRProvider` dans `src/ocr/providers/native_provider.py`
- [ ] Implémente `OCRProvider` interface
- [ ] Détection auto de la plateforme:
  - macOS → AppleScript Vision framework
  - Linux → Tesseract OCR (si installé)
  - Windows → (Future: Windows OCR API)
- [ ] Méthode `is_available() -> bool` pour vérifier disponibilité
- [ ] Cache résultats (`${storage_root}/cache/ocr/{sha256}.json`)
- [ ] Gestion erreurs avec messages clairs
- [ ] Tests sur macOS (AppleScript) avec documents de test

**Estimation:** 5 points  
**Dépendances:** US-022 (interfaces)  
**Note:** V1 = macOS. Tesseract Linux = stub avec `NotImplementedError` clair.

---

#### US-025a: Benchmark OCR Vision Models [MUST] 📋
**En tant que** développeur  
**Je veux** comparer Qwen2.5-VL (GGUF+mmproj) vs Ollama llava  
**Afin de** choisir le meilleur modèle pour l'OCR de tableaux

**Intention:** Valider expérimentalement quel modèle vision donne les meilleurs résultats avant d'implémenter le provider.

**Contexte:**
- Qwen2.5-VL en GGUF local avec mmproj (nécessite llama-cpp-python)
- Ollama llava (facile à intégrer, gestion automatique)
- Critères: qualité OCR tableaux, vitesse, consommation mémoire

**Critères d'acceptation:**
- [ ] Script `scripts/benchmark_ocr_vlm.py`
- [ ] Dataset de test: 10 images (5 tableaux complexes, 5 texte simple)
  - Documents comptables, bulletins scolaires, formulaires
- [ ] Métriques collectées:
  - Précision OCR (vs ground truth manuel)
  - Temps d'inférence (ms)
  - RAM utilisée (MB)
  - Qualité extraction tableaux (structure JSON)
- [ ] Rapport Markdown généré: `docs/BENCHMARK_OCR_VLM.md`
- [ ] Recommandation claire pour US-025

**Estimation:** 3 points  
**Dépendances:** Aucune (standalone benchmark)

---

#### US-025: Qwen-VL Provider [SHOULD] 📋
**En tant que** système  
**Je veux** utiliser Qwen-VL pour les documents complexes avec tableaux  
**Afin d'** extraire texte + structure des tableaux avec précision

**Intention:** Provider haute qualité pour documents complexes. Plus lent mais précis pour tableaux et layouts difficiles.

**Critères d'acceptation:**
- [ ] Classe `QwenVLProvider` dans `src/ocr/providers/qwen_vl_provider.py`
- [ ] Implémente `OCRProvider` interface
- [ ] Charge modèle via Ollama (`config.yaml` → `ocr.qwen_vl.model`)
- [ ] Extraction tableaux: JSON structuré `{table_id, headers, rows}`
- [ ] Prompt engineering pour extraction précise
- [ ] Cache résultats
- [ ] Tests avec documents de test (tableaux, chinois traditionnel)

**Estimation:** 5 points  
**Dépendances:** US-022 (interfaces), US-016 (OllamaClient)  
**Note:** Script bench existant à refactorer en provider

---

### Epic 7: Extraction Métadonnées [COULD]

#### US-026: EXIF Extractor [COULD] 📋
**En tant que** système  
**Je veux** extraire les métadonnées EXIF des images  
**Afin d'** enrichir l'indexation avec date, lieu, appareil

**Intention:** Extraction de métadonnées directes (pas d'OCR nécessaire). Permet de rechercher "photos de Berlin juin 2025".

**Critères d'acceptation:**
- [ ] Classe `EXIFExtractor` dans `src/indexation/exif_extractor.py`
- [ ] Librairies: `piexif` ou `exifread`
- [ ] Extraction: date_taken, camera_model, gps_coordinates, dimensions, orientation
- [ ] Convertit GPS → adresse lisible (reverse geocoding local, optionnel)
- [ ] Retourne: `EXIFResult(date, location, camera, dimensions, raw_exif)`
- [ ] Indexe dans LanceDB + Meilisearch (filtres par date, lieu)
- [ ] Tests avec images JPG/HEIC (avec/sans EXIF)

**Estimation:** 3 points  
**Dépendances:** US-012 (DocumentIndexer)  
**Note:** Indépendant de l'OCR - extraction directe de métadonnées binaires.

---

## Sprint 5: Traduction (2 semaines - Avr-Mai 2026)

**Architecture:** Pipeline de traduction modulaire via LLM.  
**Principe:** Séparation claire entre traduction pure, extraction d'actions, et exposition API.

```
src/translation/
├── interfaces.py          # TranslationResult, ActionResult (dataclasses)
├── translator.py          # Traducteur zh-TW → fr/en
├── action_extractor.py    # Extraction deadlines, tasks, entités
└── prompts/
    ├── translation.txt    # Prompt optimisé traduction formelle
    └── extraction.txt     # Prompt extraction structurée
```

### Epic 8: Translation Pipeline [MUST]

#### US-027: Créer pipeline de traduction [MUST] 📋
**En tant que** utilisateur  
**Je veux** traduire des documents chinois traditionnels  
**Afin de** les comprendre en français/anglais

**Intention:** Traduction de qualité humaine, contextualisée pour documents formels (comptabilité, école, administration).

**Critères d'acceptation:**
- [ ] Dataclasses dans `src/translation/interfaces.py`:
  - `TranslationResult(source_text, translation_fr, translation_en, confidence, model_used)`
- [ ] Classe `Translator` dans `src/translation/translator.py`
- [ ] Utilise `OllamaClient` (`config.yaml` → `translation.model`)
- [ ] Prompt engineering: contexte formel, vocabulaire précis
- [ ] Cache traductions (`${storage_root}/cache/translations/{sha256}.json`)
- [ ] Tests unitaires + test avec document réel chinois

**Estimation:** 5 points  
**Dépendances:** US-016 (OllamaClient), US-003 (ConfigManager)

---

#### US-028: Extraire actions/deadlines [MUST] 📋
**En tant que** utilisateur  
**Je veux** extraire automatiquement les échéances d'un document  
**Afin de** voir immédiatement mes tâches et deadlines

**Intention:** Transformer un document passif en liste d'actions claires avec dates.

**Critères d'acceptation:**
- [ ] Dataclass `ActionResult` dans `src/translation/interfaces.py`:
  - `deadlines: list[Deadline]`, `actions: list[str]`, `entities: dict`
- [ ] Classe `ActionExtractor` dans `src/translation/action_extractor.py`
- [ ] Prompt LLM structuré pour extraire:
  - Deadlines: tâche + date + days_remaining
  - Actions: liste d'items à faire
  - Entités: noms, montants, organisations
- [ ] Parse dates multi-format (fr, en, zh-TW)
- [ ] Calcule `days_remaining` automatiquement
- [ ] Tests avec documents de test variés

**Estimation:** 5 points  
**Dépendances:** US-027 (Translator), US-016 (OllamaClient)

---

#### US-029: API endpoint /api/translate [MUST] 📋
**En tant que** utilisateur  
**Je veux** traduire un document via l'API REST  
**Afin de** l'intégrer dans mon workflow ou UI externe

**Intention:** Exposer la traduction via API standardisée.

**Critères d'acceptation:**
- [ ] Endpoint `POST /api/translate`:
  - Input: `{file_path OR text, source_lang, target_lang, extract_actions: bool}`
  - Output: `{translation, actions (si demandé), metadata}`
- [ ] Workflow interne: OCR (si image/PDF) → Translate → Extract actions (optionnel)
- [ ] Gestion erreurs avec messages clairs
- [ ] Tests unitaires + test d'intégration E2E

**Estimation:** 3 points  
**Dépendances:** US-027, US-028, US-013 (API FastAPI)

---

#### US-029b: Test E2E Translation Pipeline [MUST] 📋
**En tant que** développeur  
**Je veux** un test end-to-end du pipeline traduction  
**Afin de** valider que tout fonctionne de bout en bout

**Intention:** Appliquer les leçons du Sprint Q&A - tests E2E obligatoires.

**Critères d'acceptation:**
- [ ] Test `tests/e2e/test_translation_pipeline.py`
- [ ] Scénario complet: document chinois → API → traduction + actions
- [ ] Vérifie: qualité traduction, extraction dates, réponse API
- [ ] Utilise vrai document de test (pas mock)
- [ ] Intégré dans CI

**Estimation:** 2 points  
**Dépendances:** US-029

---

## Sprint 6: Catégorisation (2 semaines - Mai 2026)

**Architecture:** Catégorisation intelligente via LLM avec boucle de feedback.  
**Principe:** L'utilisateur peut toujours corriger, et le système apprend de ses erreurs.

```
src/indexation/
├── categorizer.py         # Auto-catégorisation via LLM
└── category_manager.py    # Gestion corrections + feedback

config/
└── categories.yaml        # Définitions des catégories
```

### Epic 9: Category Management [SHOULD]

#### US-030: Auto-catégoriser documents [SHOULD] 📋
**En tant que** système  
**Je veux** catégoriser automatiquement les documents lors de l'indexation  
**Afin de** permettre des recherches filtrées par catégorie

**Intention:** Classification intelligente basée sur le contenu, pas juste le chemin du fichier.

**Critères d'acceptation:**
- [ ] Classe `Categorizer` dans `src/indexation/categorizer.py`
- [ ] Charge catégories depuis `config/categories.yaml` (avec keywords multilingues)
- [ ] LLM analyse: titre + premiers 1000 mots + path hints
- [ ] Retourne: `CategoryResult(category, confidence, alternative_categories)`
- [ ] Si `confidence < 0.7` → flag `needs_review = True`
- [ ] Intégré dans `DocumentIndexer` (optionnel via config)
- [ ] Tests avec documents variés (enterprise, school, news, etc.)

**Estimation:** 5 points  
**Dépendances:** US-016 (OllamaClient), US-003 (ConfigManager)

---

#### US-031: API correction catégories [SHOULD] 📋
**En tant que** utilisateur  
**Je veux** corriger une catégorie erronée via l'API  
**Afin que** le système apprenne de mes corrections

**Intention:** L'utilisateur garde le contrôle. Ses corrections améliorent le système.

**Critères d'acceptation:**
- [ ] Endpoint `PUT /api/documents/{doc_id}/category`
  - Input: `{new_category, reason (optionnel)}`
  - Output: `{success, old_category, new_category}`
- [ ] Met à jour metadata dans LanceDB + Meilisearch
- [ ] Sauvegarde correction dans `${storage_root}/corrections/corrections.json`
- [ ] Format correction: `{doc_sha256, old_category, new_category, reason, timestamp}`
- [ ] Tests unitaires + intégration

**Estimation:** 3 points  
**Dépendances:** US-013 (API), US-030 (Categorizer)

---

#### US-032: Feedback loop catégorisation [COULD] 📋
**En tant que** système  
**Je veux** utiliser les corrections passées pour améliorer les futures catégorisations  
**Afin d'** augmenter la précision au fil du temps

**Intention:** Apprentissage continu sans fine-tuning (few-shot learning via prompt).

**Critères d'acceptation:**
- [ ] Classe `CategoryFeedbackLoop` dans `src/indexation/category_manager.py`
- [ ] Lit les N dernières corrections depuis `corrections.json`
- [ ] Injecte exemples dans le prompt système du Categorizer
- [ ] Format: "Document X était classé 'leisure' mais corrigé en 'news' car: raison"
- [ ] Limite: max 5 exemples pour éviter prompt trop long
- [ ] Tests avec corrections simulées

**Estimation:** 3 points  
**Dépendances:** US-031  
**Note:** Nice-to-have. Si temps limité, peut être différé au Sprint 7.

---

#### US-032b: Test E2E Catégorisation [SHOULD] 📋
**En tant que** développeur  
**Je veux** un test end-to-end du workflow catégorisation  
**Afin de** valider la chaîne complète : index → catégoriser → corriger → re-catégoriser

**Intention:** Appliquer les leçons du Sprint Q&A.

**Critères d'acceptation:**
- [ ] Test `tests/e2e/test_categorization_pipeline.py`
- [ ] Scénario: indexer doc → vérifier catégorie → corriger → vérifier correction
- [ ] Vérifie persistance dans LanceDB + Meilisearch
- [ ] Intégré dans CI

**Estimation:** 2 points  
**Dépendances:** US-031

---

## Sprint 7: Dashboard & Polish (2 semaines - Juin 2026)

**Architecture:** Monitoring, automatisation et finalisation pour usage quotidien.  
**Principe:** AItao doit "juste marcher" sans intervention manuelle.

```
src/
├── dashboard/
│   └── tui.py             # Dashboard Rich TUI
├── core/
│   └── system_monitor.py  # Monitoring CPU/RAM/Disk
scripts/
└── daily_scan.sh          # Cronjob scan quotidien
```

### Epic 10: CLI & Dashboard [SHOULD]

#### US-033: Dashboard TUI enrichi [SHOULD] 📋
**En tant que** utilisateur  
**Je veux** voir un dashboard complet du système en terminal  
**Afin de** monitorer AItao d'un coup d'œil

**Intention:** Le `./aitao.sh status` actuel est fonctionnel mais basique. Version améliorée avec refresh auto.

**Critères d'acceptation:**
- [ ] Script `src/dashboard/tui.py` avec Rich
- [ ] Affiche:
  - Services: API (port), Worker, LanceDB, Meilisearch (avec ✓/✗)
  - Stats: Documents indexés, taille DB, queue en attente
  - Resources: CPU %, RAM (GB), Disk (GB)
  - Activité récente: 5 dernières opérations
- [ ] Mode watch: refresh toutes les 5 secondes (`--watch`)
- [ ] Couleurs: vert (OK), jaune (warning), rouge (erreur)
- [ ] Accessible via `./aitao.sh dashboard` ou `./aitao.sh status --watch`

**Estimation:** 5 points  
**Dépendances:** US-005 (CLI)

---

#### US-034: Cronjob daily scan [MUST] 📋
**En tant que** système  
**Je veux** scanner automatiquement les volumes configurés chaque jour  
**Afin d'** indexer les nouveaux fichiers sans intervention

**Intention:** Indexation "set and forget" - l'utilisateur configure une fois, puis oublie.

**Critères d'acceptation:**
- [ ] Script `scripts/daily_scan.sh`
- [ ] Appelle `./aitao.sh scan --volumes prod` (volumes de production)
- [ ] Instructions installation cron: `crontab -e` → `0 2 * * * /path/to/daily_scan.sh`
- [ ] Log JSON dans `${logs_dir}/daily_scan_YYYY-MM-DD.log`
- [ ] Résumé final: "X nouveaux, Y modifiés, Z erreurs"
- [ ] Option notification (macOS: osascript notification)
- [ ] Tests avec exécution manuelle

**Estimation:** 2 points  
**Dépendances:** US-008 (FilesystemScanner)

---

#### US-035: System load monitor [SHOULD] 📋
**En tant que** système  
**Je veux** détecter la charge système et l'activité utilisateur  
**Afin de** throttler les tâches background quand le Mac est utilisé

**Intention:** AItao ne doit jamais ralentir le travail de l'utilisateur.

**Critères d'acceptation:**
- [ ] Classe `SystemMonitor` dans `src/core/system_monitor.py`
- [ ] Méthodes:
  - `get_cpu_percent() -> float`
  - `get_memory_usage() -> MemoryInfo(used_gb, total_gb, percent)`
  - `get_disk_usage(path) -> DiskInfo(used_gb, total_gb, percent)`
  - `is_user_active() -> bool` (macOS: dernière activité clavier/souris < 60s)
  - `should_throttle() -> bool` (CPU >80% OR user active)
- [ ] Worker utilise `should_throttle()` pour pauser
- [ ] Tests unitaires (avec mocks pour ressources système)

**Estimation:** 3 points  
**Dépendances:** US-010 (Worker)

---

### Epic 11: Testing & Documentation [SHOULD]

#### US-036: Tests end-to-end complets [MUST] 📋
**En tant que** développeur  
**Je veux** une suite de tests E2E couvrant tous les workflows critiques  
**Afin de** garantir que AItao fonctionne en conditions réelles

**Intention:** Leçon majeure du Sprint Q&A - les tests unitaires avec mocks ne suffisent pas.

**Critères d'acceptation:**
- [ ] Dossier `tests/e2e/` avec tests d'intégration complets
- [ ] Scénarios obligatoires:
  1. `test_ingest_to_search.py`: Scan → Queue → Worker → Index → Search → Résultat
  2. `test_ocr_pipeline.py`: Image/PDF → OCR Router → Extraction → Index
  3. `test_translation_e2e.py`: Document chinois → Traduction → Actions
  4. `test_api_endpoints.py`: Tous les endpoints critiques
  5. `test_startup_shutdown.py`: Lifecycle complet des services
- [ ] Dataset de test réel (pas mocks): `tests/fixtures/`
- [ ] Tous les tests passent en CI (GitHub Actions)
- [ ] Coverage rapport généré

**Estimation:** 8 points  
**Dépendances:** Sprints 4, 5, 6

---

#### US-037: Documentation utilisateur finale [SHOULD] 📋
**En tant que** nouvel utilisateur  
**Je veux** une documentation claire et complète  
**Afin d'** installer, configurer et utiliser AItao

**Intention:** Un utilisateur non-technique doit pouvoir installer et utiliser AItao en suivant le README.

**Critères d'acceptation:**
- [ ] `README.md` mis à jour avec:
  - Quickstart (5 min)
  - Installation détaillée (macOS)
  - Configuration (`config.yaml` expliqué)
  - Commandes CLI (avec exemples)
  - Intégration Continue.dev / Open WebUI / AnythingLLM
- [ ] `docs/TROUBLESHOOTING.md`: problèmes courants + solutions
- [ ] `docs/API.md`: documentation API (ou lien vers `/docs`)
- [ ] `docs/ARCHITECTURE.md`: vue d'ensemble pour développeurs
- [ ] Capture d'écran du dashboard

**Estimation:** 5 points  
**Dépendances:** US-036

---

#### US-037b: Validation finale et release V2.4 [MUST] 📋
**En tant que** développeur  
**Je veux** une checklist de validation complète avant release  
**Afin de** m'assurer que V2.4 est prête pour usage quotidien

**Intention:** Pas de "ça marche sur ma machine" - validation rigoureuse.

**Critères d'acceptation:**
- [ ] Tous les tests passent (`pytest` + E2E)
- [ ] `./aitao.sh start` démarre tous les services sans erreur
- [ ] Health check OK (`curl localhost:8200/api/health`)
- [ ] Indexation d'un nouveau document fonctionne
- [ ] Recherche retourne des résultats pertinents
- [ ] OCR fonctionne (au moins native provider)
- [ ] Traduction fonctionne
- [ ] Continue.dev connecté et fonctionnel
- [ ] Version bumped → `2.4.0`
- [ ] Tag Git créé
- [ ] CHANGELOG mis à jour

**Estimation:** 2 points  
**Dépendances:** Tous les US du sprint

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
