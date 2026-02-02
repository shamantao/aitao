# AItao V2.0 - Backlog TODO

**Date:** February 2, 2026  
**Branch:** `pdr/v2-remodular`  
**Priorité:** MOSCOW (Must/Should/Could/Won't)  
**Version actuelle:** 2.4.27

---

## 🏁 Sprint Summary

| Sprint | Status | User Stories | Tests | Version |
|--------|--------|--------------|-------|---------|
| Sprint 0: Foundation | ✅ Complete | US-001 → US-007b | 85 | v2.0.5 → v2.1.8 |
| Sprint 1: Indexation | ✅ Complete | US-008 → US-010 | 218 | v2.1.9 → v2.1.11 |
| Sprint 2: Recherche | ✅ Complete | US-011 → US-015 | 370 | v2.2.11 → v2.2.15 |
| **Sprint 2b: Search Optimization** | ✅ **Complete** | US-014b | +5 | **v2.3.22** |
| Sprint 3: RAG & LLM | ✅ Complete | US-016 → US-021 | 461 | v2.3.16 → v2.3.20 |
| **Sprint 3b: Model Management** | 📋 Pending | US-021b → US-021f | - | v2.3.22.x |
| **Sprint 3c: Virtual Models** | ✅ Complete | US-021g → US-021i | - | v2.3.21.x |
| Sprint Q&A: Vérifications | ✅ Complete | QA-001 → QA-006 | - | v2.3.21.x |
| **Sprint 4: Chunking & Quick Wins** | 🚧 **EN COURS** | US-023 → US-028 | 519+ | **v2.4.x** |
| Sprint 5: OCR & Extraction Avancée | 📋 Pending | US-030 → US-034 | - | v2.5.x |
| Sprint 6: Traduction | 📋 Pending | US-035 → US-037b | - | v2.6.x |
| Sprint 7: Catégorisation | 📋 Pending | US-038 → US-040b | - | v2.7.x |
| Sprint 8: Dashboard & Polish | 📋 Pending | US-041 → US-045b | - | v2.8.x |

> 📎 Voir [backlog-done.md](backlog-done.md) pour les sprints terminés (0, 1, 2, 2b, 3, 3c, Q&A)

---

## 📝 Décisions & Changelog

### 🔧 v2.4.27 (2026-02-02) - EXIF + Office Extractors

**Nouvelles fonctionnalités:**
- US-024: TextExtractor amélioré (.csv, .log, file size limit, get_logger)
- US-025: Office extractors (PPTXExtractor, XLSXExtractor, ODFExtractor)
- US-027: EXIFExtractor pour métadonnées images
- **58 extensions** maintenant supportées

**Décisions:**
- US-026 (emails .eml) → DROPPED (faible priorité)
- US-028 (WebSearch DDG) → PARKING LOT (responsabilité UI, pas AiTao)
- Renumbering: US-028b (PDF) → US-028, US-034 (Actions/Deadline) → US-029

### 🔧 v2.4.23.2 (2026-02-02) - Architecture Contracts

- US-023b: Migration Registry/PathManager + StatsKeys
- Pre-commit hook pour contracts (AC-001 à AC-007)
- `./aitao.sh contracts` command ajoutée

### 🔧 Hotfix v2.3.23 (2026-02-02) - CLI Stats Display Fix

**Problème résolu:** `./aitao.sh index status` affichait 0 documents
- **Cause:** Clés de stats incohérentes (`document_count` vs `total_documents`)
- **Fix:** Alignement des clés dans `cli/commands/index.py`

### 🔧 Hotfix v2.3.22 (2026-02-01) - Search Optimization

**Problème résolu:** La recherche échouait sur les requêtes courtes françaises

**Solution:**
- **Query Expansion** : "CV" → "cv curriculum vitae resume 履歷"
- **Reciprocal Rank Fusion (RRF)** : Meilleure fusion que weighted average
- **Config fix** : Section `rag` déplacée au niveau racine

---

## 🅿️ PARKING LOT

> User Stories mises de côté - décision en attente

### US-PL-001: Recherche web DuckDuckGo [DECISION PENDING]
**Origine:** US-028 (Sprint 4)  
**Question:** Est-ce la responsabilité d'AiTao ou de l'UI (Open WebUI, AnythingLLM) ?

**En tant que** utilisateur  
**Je veux** que le LLM puisse chercher sur le web  
**Afin d'** avoir des informations à jour quand mes documents ne suffisent pas

**Critères d'acceptation:**
- [ ] Tool `web_search` dans `src/tools/web_search.py`
- [ ] Utilise DuckDuckGo API (ou scraping léger)
- [ ] Retourne: top 5 résultats avec title, snippet, url
- [ ] Rate limiting pour éviter blocage

**Estimation:** 3 points  
**Status:** 🅿️ PARKING LOT - à réévaluer après Sprint 5

---

## Sprint 4: Chunking & Quick Wins (3 semaines - Fév-Mar 2026)

**Objectif:** Avant d'attaquer l'OCR (coûteux en ressources), maximiser ce qui est facilement indexable.  
**Stratégie:** Quick Wins d'abord = résultats rapides, puis chunking = qualité RAG.

```
Priorités Sprint 4:
├── 🎯 US-023: Chunking Pipeline (CRITIQUE - fixe le problème contexte RAG) ✅
├── 🔧 US-023b: Migration Registry/PathManager ✅
├── ⚡ US-024: Extraction texte pur (.txt, .md, .json) ✅
├── ⚡ US-025: Extraction Office (.docx, .pptx, .xlsx, .ods) ✅
├── ❌ US-026: Extraction emails (.eml) - DROPPED
├── ⚡ US-027: Extraction EXIF images (métadonnées seulement) ✅
├── 📄 US-028: Extraction PDF texte pur (ex-US-028b)
└── ⏰ US-029: Extraction Actions/Deadlines (ex-US-034)
```

### 📊 Analyse Volumes Production

| Type | Fichiers | Taille | Difficulté | Priorité | Status |
|------|----------|--------|------------|----------|--------|
| .txt/.md/.json | 1,653 | 60 MB | ⭐ Trivial | P0 | ✅ DONE |
| .docx/.pptx/.xlsx/.ods | 287 | 880 MB | ⭐⭐ Facile | P0 | ✅ DONE |
| .jpg/.png (EXIF) | 2,206 | 2 GB | ⭐ Trivial | P1 | ✅ DONE |
| .pdf (texte) | ~500 | ~600 MB | ⭐⭐ Moyen | P1 | 📋 TODO |
| .pdf (scannés) | ~600 | ~700 MB | ⭐⭐⭐⭐ OCR requis | P2 | Sprint 5 |

---

### Epic 5: Chunking Pipeline [MUST] ✅ DONE

#### US-023: Chunking Pipeline pour RAG [MUST] ✅ DONE
**Status:** ✅ **TERMINÉ le 2026-02-02**  
**Version:** 2.4.23

- ChunkingPipeline: `src/indexation/chunker.py`
- ChunkStore: `src/indexation/chunk_store.py`
- **2072 chunks** indexés pour **271 documents**

---

#### US-023b: Migration Registry & PathManager [MUST] ✅ DONE
**Status:** ✅ **TERMINÉ le 2026-02-02**  
**Version:** 2.4.23.2

- StatsKeys dans Registry
- Pre-commit hook pour architecture contracts
- 519 unit tests passent

---

### Epic 6: Quick Wins - Extraction Texte [MUST]

#### US-024: Extraction texte pur [MUST] ✅ DONE
**Status:** ✅ **TERMINÉ le 2026-02-02**  
**Version:** 2.4.24

- Supporte: `.txt`, `.md`, `.json`, `.yaml`, `.csv`, `.log`
- Limite taille configurable (max_file_size_mb)
- get_logger migration

---

#### US-025: Extraction Office [MUST] ✅ DONE
**Status:** ✅ **TERMINÉ le 2026-02-02**  
**Version:** 2.4.25

- PPTXExtractor, XLSXExtractor, ODFExtractor ajoutés
- Supporte: `.docx`, `.pptx`, `.xlsx`, `.odt`, `.ods`, `.odp`

---

#### US-026: Extraction emails (.eml) [WON'T] ❌ DROPPED
**Raison:** Faible priorité - abandonné.

---

#### US-027: Extraction EXIF images [SHOULD] ✅ DONE
**Status:** ✅ **TERMINÉ le 2026-02-02**  
**Version:** 2.4.27

- EXIFExtractor dans `text_extractor.py`
- Supporte: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.webp`
- Extraction: date_taken, camera_model, GPS, dimensions
- Dépendance: `Pillow>=10.0.0`

---

### Epic 7: PDF Texte Extractible [SHOULD]

#### US-028: Extraction PDF texte pur [SHOULD] 📋
**En tant que** système  
**Je veux** extraire le texte des PDF non-scannés  
**Afin d'** indexer rapidement les PDF natifs (sans OCR)

**Intention:** ~50% des PDF contiennent du texte extractible. OCR = Sprint 5.

**Critères d'acceptation:**
- [ ] `PDFExtractor` amélioré dans `src/indexation/text_extractor.py`
- [ ] Librairie: `pdfplumber` ou `pypdf2`
- [ ] Détection: PDF texte vs PDF scanné (image)
- [ ] Si texte: extraction directe
- [ ] Si scanné: flag `needs_ocr = True` pour Sprint 5
- [ ] Métadonnées: auteur, title, page_count
- [ ] Intégré dans `DocumentIndexer` + chunking
- [ ] Tests avec PDF variés
- [ ] **Conformité PRD Architecture:**
  - [ ] Utiliser `get_logger(__name__)` pour logging
  - [ ] Docstrings et commentaires en anglais
  - [ ] Fichier < 350 lignes (ou refactoring extracteurs)

**Estimation:** 3 points  
**Dépendances:** US-023 (Chunking)

---

### Epic 8: Actions & Deadlines [SHOULD]

#### US-029: Extraire actions/deadlines [SHOULD] 📋
**En tant que** utilisateur  
**Je veux** extraire automatiquement les échéances d'un document  
**Afin de** voir immédiatement mes tâches et deadlines

**Intention:** Transformer un document passif en liste d'actions claires avec dates.

**Critères d'acceptation:**
- [ ] Dataclass `ActionResult` dans `src/extraction/interfaces.py`:
  - `deadlines: list[Deadline]`, `actions: list[str]`, `entities: dict`
- [ ] Classe `ActionExtractor` dans `src/extraction/action_extractor.py`
- [ ] Prompt LLM structuré pour extraire:
  - Deadlines: tâche + date + days_remaining
  - Actions: liste d'items à faire
  - Entités: noms, montants, organisations
- [ ] Parse dates multi-format (fr, en, zh-TW)
- [ ] Calcule `days_remaining` automatiquement
- [ ] Tests avec documents de test variés

**Estimation:** 5 points  
**Dépendances:** US-016 (OllamaClient)

---

## Sprint 5: OCR & Extraction Avancée (3 semaines - Mar-Apr 2026)

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

### Epic 9: OCR Pipeline [MUST]

#### US-030: OCR Router + Interfaces [MUST] 📋
**En tant que** développeur  
**Je veux** une architecture OCR modulaire avec interfaces claires  
**Afin de** pouvoir remplacer n'importe quel provider sans casser le système

**Critères d'acceptation:**
- [ ] Interface abstraite `OCRProvider` dans `src/ocr/interfaces.py`
- [ ] Dataclass `OCRResult` dans `src/ocr/interfaces.py`
- [ ] Classe `OCRRouter` dans `src/ocr/router.py`
- [ ] Config `config.yaml` → `ocr.default_provider`, `ocr.providers`
- [ ] Tests: mock providers pour valider le routing

**Estimation:** 5 points  
**Dépendances:** US-001 (PathManager), US-003 (ConfigManager)

---

#### US-031: Table Detector [SHOULD] 📋
**En tant que** système  
**Je veux** détecter la présence de tableaux dans les documents  
**Afin de** router vers Qwen-VL quand nécessaire

**Estimation:** 3 points  
**Dépendances:** US-030 (OCR Router)

---

#### US-032: Native OCR Provider (macOS/Linux) [MUST] 📋
**En tant que** système  
**Je veux** un provider OCR natif selon la plateforme  
**Afin d'** extraire le texte sans GPU ni modèle lourd

**Estimation:** 5 points  
**Dépendances:** US-030 (OCR Router)

---

#### US-033: Qwen-VL Provider (tableaux/complexe) [SHOULD] 📋
**En tant que** système  
**Je veux** utiliser Qwen-VL pour les documents complexes  
**Afin d'** extraire les tableaux et layouts difficiles

**Estimation:** 5 points  
**Dépendances:** US-030, US-031, US-016 (OllamaClient)

---

#### US-034: Test E2E OCR Pipeline [MUST] 📋
**En tant que** développeur  
**Je veux** un test end-to-end du pipeline OCR complet  
**Afin de** valider la chaîne : image → router → provider → texte

**Estimation:** 2 points  
**Dépendances:** US-032, US-033

---

## Sprint 6: Traduction (2 semaines - Avr-Mai 2026)

**Architecture:** Pipeline de traduction modulaire via LLM.

```
src/translation/
├── interfaces.py          # TranslationResult (dataclass)
├── translator.py          # Traducteur zh-TW → fr/en
└── prompts/
    └── translation.txt    # Prompt optimisé traduction formelle
```

### Epic 10: Translation Pipeline [MUST]

#### US-035: Créer pipeline de traduction [MUST] 📋
**En tant que** utilisateur  
**Je veux** traduire des documents chinois traditionnels  
**Afin de** les comprendre en français/anglais

**Estimation:** 5 points  
**Dépendances:** US-016 (OllamaClient)

---

#### US-036: API endpoint /api/translate [MUST] 📋
**Estimation:** 3 points  
**Dépendances:** US-035

---

#### US-037: Test E2E Translation Pipeline [MUST] 📋
**Estimation:** 2 points  
**Dépendances:** US-036

---

## Sprint 7: Catégorisation (2 semaines - Mai-Juin 2026)

**Architecture:** Catégorisation intelligente via LLM avec boucle de feedback.

### Epic 11: Category Management [SHOULD]

#### US-038: Auto-catégoriser documents [SHOULD] 📋
**Estimation:** 5 points

---

#### US-039: API correction catégories [SHOULD] 📋
**Estimation:** 3 points

---

#### US-040: Feedback loop catégorisation [COULD] 📋
**Estimation:** 3 points

---

#### US-040b: Test E2E Catégorisation [SHOULD] 📋
**Estimation:** 2 points

---

## Sprint 8: Dashboard & Polish (2 semaines - Juin-Juil 2026)

### Epic 12: CLI & Dashboard [SHOULD]

#### US-041: Dashboard TUI enrichi [SHOULD] 📋
**Estimation:** 5 points

---

#### US-042: Cronjob daily scan [MUST] 📋
**Estimation:** 2 points

---

#### US-043: System load monitor [SHOULD] 📋
**Estimation:** 3 points

---

### Epic 13: Testing & Documentation [SHOULD]

#### US-044: Tests end-to-end complets [MUST] 📋
**Estimation:** 8 points

---

#### US-045: Documentation utilisateur finale [SHOULD] 📋
**Estimation:** 5 points

---

#### US-045b: Validation finale et release V2.4 [MUST] 📋
**Estimation:** 2 points

---

## Backlog (Future - V3+)

### Epic 14: Multi-platform [WON'T - V3]

- **US-046:** Support Linux
- **US-047:** Support Windows
- **US-048:** Docker full stack

### Epic 15: Advanced Features [WON'T - V3]

- **US-049:** Email indexing (Gmail, Outlook)
- **US-050:** Audio/Video transcription
- **US-051:** Image generation (local)
- **US-052:** Encryption at-rest
- **US-053:** Multi-user support

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

---

## Points d'estimation

- **1 point:** 1-2 heures (trivial)
- **2 points:** 3-4 heures (simple)
- **3 points:** 1 jour (moyen)
- **5 points:** 2-3 jours (complexe)
- **8 points:** 4-5 jours (très complexe, à décomposer)

---

**Velocity cible:** 20-25 points/sprint (1 dev, 2 semaines)
