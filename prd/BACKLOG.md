# AItao V2.0 - Backlog Agile

**Date:** January 28, 2026  
**Branch:** `pdr/v2-remodular`  
**Priorité:** MOSCOW (Must/Should/Could/Won't)

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

#### US-005: Créer CLI aitao.sh [MUST] 🔄
**En tant que** utilisateur  
**Je veux** un script shell pour gérer AItao  
**Afin de** démarrer/arrêter/vérifier les services

**Critères d'acceptation:**
- [ ] Script `aitao.sh` avec commandes: start, stop, status, ingest, search, logs, config
- [ ] `aitao.sh start`: Lance API, worker, cronjob
- [ ] `aitao.sh stop`: Arrête proprement tous les services
- [ ] `aitao.sh status`: Affiche dashboard TUI
- [ ] `aitao.sh ingest <path>`: Ingestion manuelle
- [ ] `aitao.sh search "query"`: Recherche en CLI
- [ ] `aitao.sh logs <module>`: Affiche les logs
- [ ] `aitao.sh config validate`: Valide config.yaml

**Estimation:** 5 points  
**Dépendances:** US-001, US-002, US-003

---

### Epic 2: Base de données [MUST]

#### US-006: Intégrer LanceDB [MUST] 📋
**En tant que** système  
**Je veux** un index vectoriel local  
**Afin de** faire de la recherche sémantique

**Critères d'acceptation:**
- [ ] Classe `LanceDBClient` dans `src/search/lancedb_client.py`
- [ ] Connexion à LanceDB (`${storage_root}/lancedb`)
- [ ] Schéma: id (sha256), path, title, content, embeddings, metadata
- [ ] Méthodes: `add_document()`, `search()`, `delete()`, `get_stats()`
- [ ] Embeddings avec `sentence-transformers/all-MiniLM-L6-v2`
- [ ] Tests unitaires avec documents de test

**Estimation:** 5 points  
**Dépendances:** US-001, US-003

---

#### US-007: Intégrer Meilisearch [MUST] 📋
**En tant que** système  
**Je veux** un moteur de recherche full-text  
**Afin de** faire de la recherche rapide avec filtres

**Critères d'acceptation:**
- [ ] Classe `MeilisearchClient` dans `src/search/meilisearch_client.py`
- [ ] Connexion à Meilisearch host (`localhost:7700`)
- [ ] Création index `aitao_documents` avec filtres: date, path, category, language
- [ ] Méthodes: `add_document()`, `search()`, `delete()`, `get_stats()`
- [ ] Gestion des erreurs (connexion, index missing)
- [ ] Tests unitaires avec documents de test

**Estimation:** 5 points  
**Dépendances:** US-001, US-003

---

## Sprint 1: Indexation basique (2 semaines - Fév 2026)

### Epic 3: Filesystem Scanning [MUST]

#### US-008: Scanner filesystem [MUST] 📋
**En tant que** système  
**Je veux** scanner les volumes configurés  
**Afin de** détecter les nouveaux fichiers

**Critères d'acceptation:**
- [ ] Classe `FilesystemScanner` dans `src/indexation/scanner.py`
- [ ] Lit `config.yaml` → `paths.test_volumes` / `paths.prod_volumes`
- [ ] Parcourt récursivement les volumes
- [ ] Skip patterns: `.*`, `__pycache__`, `node_modules`, `.git`
- [ ] Filtre par extensions supportées (config.yaml)
- [ ] Compare mtime + SHA256 pour détecter modifications
- [ ] Retourne liste de fichiers nouveaux/modifiés
- [ ] Tests unitaires avec filesystem de test

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager)

---

#### US-009: Créer système de queue [MUST] 📋
**En tant que** système  
**Je veux** une queue JSON pour les tâches d'indexation  
**Afin de** traiter les fichiers de manière asynchrone

**Critères d'acceptation:**
- [ ] Classe `TaskQueue` dans `src/indexation/queue.py`
- [ ] Fichier JSON: `${storage_root}/queue/tasks.json`
- [ ] Structure: `[{id, file_path, task_type, priority, added_at, status}]`
- [ ] Méthodes: `add_task()`, `get_next_task()`, `update_status()`, `get_stats()`
- [ ] Priorités: `high`, `normal`, `low`
- [ ] Statuts: `pending`, `processing`, `completed`, `failed`
- [ ] Thread-safe (file locking)
- [ ] Tests unitaires

**Estimation:** 3 points  
**Dépendances:** US-001 (PathManager)

---

#### US-010: Créer background worker [MUST] 📋
**En tant que** système  
**Je veux** un worker qui traite la queue  
**Afin de** indexer les fichiers en arrière-plan

**Critères d'acceptation:**
- [ ] Script `src/indexation/worker.py`
- [ ] Boucle infinie: poll queue toutes les 30 secondes
- [ ] Traite les tâches séquentiellement (1 à la fois)
- [ ] Vérifie charge système (CPU <80%) avant traitement
- [ ] Met à jour statut tâche: `pending` → `processing` → `completed`/`failed`
- [ ] Log chaque étape (JSON)
- [ ] Daemon mode (background process)
- [ ] Tests avec queue simulée

**Estimation:** 5 points  
**Dépendances:** US-009 (TaskQueue), US-002 (Logger)

---

### Epic 4: Indexation texte direct [MUST]

#### US-011: Extraire texte direct (PDF, DOCX) [MUST] 📋
**En tant que** système  
**Je veux** extraire le texte des documents  
**Afin de** les indexer sans OCR

**Critères d'acceptation:**
- [ ] Classe `TextExtractor` dans `src/indexation/text_extractor.py`
- [ ] PDF: `pdfminer.six` ou `pypdf`
- [ ] DOCX: `python-docx`
- [ ] TXT, MD, JSON, TOML: lecture directe
- [ ] Code (.py, .js, .ts): lecture directe
- [ ] Retourne: `{text, metadata: {pages, word_count, language}}`
- [ ] Détecte langue (langdetect)
- [ ] Tests avec fichiers de test

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager)

---

#### US-012: Indexer documents dans LanceDB + Meilisearch [MUST] 📋
**En tant que** système  
**Je veux** indexer les documents extraits  
**Afin de** permettre la recherche

**Critères d'acceptation:**
- [ ] Classe `DocumentIndexer` dans `src/indexation/indexer.py`
- [ ] Workflow: Extract text → Generate embeddings → Index LanceDB + Meilisearch
- [ ] Calcule SHA256 (déduplication)
- [ ] Extrait metadata: path, mtime, size, language, category (TBD)
- [ ] Ajoute à LanceDB (embeddings)
- [ ] Ajoute à Meilisearch (full-text + filtres)
- [ ] Log succès/erreurs
- [ ] Tests end-to-end

**Estimation:** 5 points  
**Dépendances:** US-006 (LanceDB), US-007 (Meilisearch), US-011 (TextExtractor)

---

## Sprint 2: Recherche hybride (2 semaines - Mars 2026)

### Epic 5: Search API [MUST]

#### US-013: Créer API REST FastAPI [MUST] 📋
**En tant que** développeur  
**Je veux** une API REST pour accéder à AItao  
**Afin de** intégrer avec Continue/Wave/Custom UI

**Critères d'acceptation:**
- [ ] FastAPI app dans `src/api/main.py`
- [ ] Endpoints: `/api/search`, `/api/ingest`, `/api/health`, `/api/stats`
- [ ] CORS configuré (`config.yaml` → `api.cors_origins`)
- [ ] Port configurable (défaut: 5000)
- [ ] Documentation OpenAPI auto-générée (`/docs`)
- [ ] Logging des requêtes
- [ ] Tests unitaires + intégration

**Estimation:** 5 points  
**Dépendances:** US-003 (ConfigManager), US-002 (Logger)

---

#### US-014: Implémenter recherche hybride [MUST] 📋
**En tant que** utilisateur  
**Je veux** une recherche combinant full-text + sémantique  
**Afin de** trouver mes documents rapidement

**Critères d'acceptation:**
- [ ] Endpoint `POST /api/search`
- [ ] Requête parallèle: Meilisearch + LanceDB
- [ ] Merge résultats (weighted: 40% Meilisearch, 60% LanceDB)
- [ ] Filtres: date_after, date_before, path_contains, category, language
- [ ] Retourne top 10 avec: path, title, summary, score, metadata
- [ ] Latence <3 secondes (500K documents)
- [ ] Tests avec dataset de test

**Estimation:** 8 points  
**Dépendances:** US-006 (LanceDB), US-007 (Meilisearch), US-013 (API)

---

#### US-015: Implémenter endpoint /api/health [MUST] 📋
**En tant que** système externe  
**Je veux** vérifier la santé d'AItao  
**Afin de** détecter les problèmes

**Critères d'acceptation:**
- [ ] Endpoint `GET /api/health`
- [ ] Vérifie: API running, LanceDB connected, Meilisearch connected
- [ ] Retourne JSON: `{status, services: {api, lancedb, meilisearch, worker}, timestamp}`
- [ ] Status: `healthy`, `degraded`, `down`
- [ ] Tests unitaires

**Estimation:** 2 points  
**Dépendances:** US-013 (API)

---

## Sprint 3: OCR & Extraction (3 semaines - Mars-Avr 2026)

### Epic 6: OCR Pipeline [MUST]

#### US-016: Détecter tableaux dans PDF/images [SHOULD] 📋
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

#### US-017: Intégrer AppleScript OCR [MUST] 📋
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

#### US-018: Intégrer Qwen-VL OCR [MUST] 🔄
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

#### US-019: Créer OCR Router [MUST] 📋
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
**Dépendances:** US-016, US-017, US-018

---

### Epic 7: Extraction EXIF [SHOULD]

#### US-020: Extraire métadonnées EXIF des images [SHOULD] 📋
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

## Sprint 4: Traduction (2 semaines - Avr-Mai 2026)

### Epic 8: Translation Pipeline [MUST]

#### US-021: Créer pipeline de traduction [MUST] 📋
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

#### US-022: Extraire actions/deadlines [MUST] 📋
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

#### US-023: API endpoint /api/translate [MUST] 📋
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
**Dépendances:** US-021, US-022, US-013 (API)

---

## Sprint 5: Catégorisation (2 semaines - Mai 2026)

### Epic 9: Category Management [SHOULD]

#### US-024: Auto-catégoriser documents [SHOULD] 📋
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

#### US-025: API correction catégories [SHOULD] 📋
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
**Dépendances:** US-013 (API), US-024 (Categorizer)

---

#### US-026: Feedback loop catégorisation [COULD] 🔮
**En tant que** système  
**Je veux** utiliser les corrections pour améliorer  
**Afin d'** augmenter la précision

**Critères d'acceptation:**
- [ ] Lit `corrections.json`
- [ ] Ajuste prompt système avec exemples de corrections
- [ ] Option: Fine-tuning model (V3+)
- [ ] Tests avec corrections simulées

**Estimation:** 5 points  
**Dépendances:** US-025  
**Note:** Nice-to-have, peut être déféré

---

## Sprint 6: Dashboard & Polish (2 semaines - Juin 2026)

### Epic 10: CLI & Dashboard [SHOULD]

#### US-027: Dashboard TUI (status) [SHOULD] 📋
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

#### US-028: Cronjob daily scan [MUST] 📋
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

#### US-029: System load monitor [SHOULD] 📋
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

#### US-030: Tests end-to-end [SHOULD] 📋
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

#### US-031: Documentation utilisateur [SHOULD] 📋
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
**Dépendances:** US-030

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
