# AI Tao - Vérification Cohérence Backlog vs. Intentions PRD

**Date:** 22 janvier 2026  
**Objectif:** Valider que chaque story du backlog sert les intentions fondamentales

---

## ✅ Grille d'Analyse : Story vs. Intentions

| Story ID | Titre | Sert l'Intention ? | Priorité Alignée ? | Notes |
|----------|-------|-------------------|-------------------|-------|
| **AITAO-001** | Fix Logger PathManager | ✅ Oui - Confidentialité | ✅ Critique | Logs doivent rester dans `storage_root` (local) |
| **AITAO-002** | Centralize PathManager | ✅ Oui - Simplicité | ✅ Critique | Architecture propre = maintenance facile |
| **AITAO-003** | SHA-256 Hash Metadata | ✅ Oui - Performance | ✅ Haute | Évite re-indexation inutile (économie ressources) |
| **AITAO-004** | Complete CLI | ✅ Oui - Simplicité | ✅ Haute | `./aitao.sh start` = "just works" |
| **AITAO-005** | Presentations Support | ✅ Oui - Cas d'usage | ✅ Haute | UC-001 : Recherche dans tous types docs |
| **AITAO-006** | Sync Agent | ✅ Oui - Simplicité | ✅ Critique | Config.toml → UI auto (pas de clics manuels) |
| **AITAO-007** | Web Search UI | ✅ Oui - Cas d'usage | ✅ Haute | UC-003 : Opt-in explicite (contrôle utilisateur) |
| **AITAO-008** | E2E Test RAG | ✅ Oui - Qualité | ✅ Critique | Garantir "ça marche" avant V1 |
| **AITAO-009** | Benchmark Indexing | ✅ Oui - Transparence | ✅ Haute | Utilisateur doit savoir "combien de temps" |
| **AITAO-010** | Vision Model | ✅ Oui - Cas d'usage | ✅ Haute | UC-002 : OCR, tableaux → Excel |
| **AITAO-011** | Code Model | ✅ Oui - Cas d'usage | ✅ Haute | UC-005 : Assistance développeur (Wave Terminal) |
| **AITAO-012** | Audio Transcription | ⚠️ Partiel - Cas d'usage | 🔮 Future | PRD mentionne mais pas priorité V1 |
| **AITAO-013** | SVG Generation | ⚠️ Partiel - Cas d'usage | 🔮 Future | PRD mentionne mais UC-004 = Future |
| **AITAO-014** | External API | ✅ Oui - Modulité | ✅ Haute | UC-005 : Wave Terminal, autres apps |
| **AITAO-015** | Watch Folders | ✅ Oui - Simplicité | ✅ Haute | "Drop file, it's indexed" = Radical Simplicity |
| **AITAO-016** | Multi-Platform | ✅ Oui - Accessibilité | 🛡️ Polish | PRD : macOS first, Linux/Windows future |
| **AITAO-017** | Zero-Config Installer | ✅ Oui - Simplicité | 🛡️ Polish | PRD : "15 min setup" = must-have long terme |
| **AITAO-018** | Metrics Dashboard | ⚠️ Indirect - Qualité | 🛡️ Polish | Aide développement, pas utilisateur final |
| **AITAO-019** | Legacy Cleanup | ✅ Oui - Clarté | 🧹 Low | Code propre = maintenance facile |

---

## 🎯 Intentions du PRD (Rappel)

### Intention #1 : Confidentialité Absolue
> "What happens on your Mac, stays on your Mac. Your data are your own."

**Stories alignées :**
- ✅ AITAO-001 (Logs locaux)
- ✅ AITAO-007 (Web search opt-in explicite)
- ✅ AITAO-018 (Metrics locales, pas de telemetry)

**Risques :**
- ❌ Aucune story sur chiffrement (PRD dit "V1 : pas de chiffrement")
- ⚠️ AITAO-010/011 (Vision/Code models) : vérifier qu'ils ne "call home"

---

### Intention #2 : Simplicité Radicale
> "L'utilisateur ne doit pas 'coder' pour 'utiliser'. Il dépose un fichier, il pose une question."

**Stories alignées :**
- ✅ AITAO-004 (CLI simple : `start/stop/status`)
- ✅ AITAO-006 (Sync auto config → UI)
- ✅ AITAO-015 (Watch folders = drop & forget)
- ✅ AITAO-017 (Zero-config installer)

**Gaps :**
- ⚠️ Pas de story sur "Onboarding UX" (premier lancement, guide rapide)
- ⚠️ Pas de story sur "Messages d'erreur en français/anglais clairs"

**Recommandation :**
Ajouter **AITAO-020 : First-Run Experience**
- Wizard au premier `./aitao.sh start`
- Guide interactif : "Où voulez-vous stocker vos données ?"
- Génération auto de `config.toml`

---

### Intention #3 : Modularité (Lego Blocks)
> "Nous connectons les meilleurs outils (Llama.cpp, AnythingLLM, scripts Python)"

**Stories alignées :**
- ✅ AITAO-002 (PathManager centralisé = swappable)
- ✅ AITAO-006 (Sync Agent = pont modulaire vers UI)
- ✅ AITAO-014 (API externe = intégration autres apps)
- ✅ AITAO-010/011 (Models swappables)

**Gaps :**
- ⚠️ Pas de story sur "Model Switcher UI" (changer de modèle sans restart)
- ⚠️ Pas de story sur "Plugin System" (ajouter outils tiers)

**Recommandation :**
Déjà bien couvert pour V1. Plugin system = V2+.

---

### Intention #4 : Préservation Environnement
> "Né du besoin de préserver l'environnement"

**Stories alignées :**
- ✅ AITAO-003 (Hash = évite re-traitement inutile)
- ✅ AITAO-009 (Benchmark = optimisation ressources)
- ⚠️ Indirect : Local > Cloud = moins de data centers

**Gaps :**
- ❌ Aucune story sur "Power Management" (sleep models quand inactif)
- ❌ Aucune story sur "Metrics énergétiques" (kWh consommé)

**Recommandation :**
Phase 2+ : **AITAO-021 : Energy-Aware Processing**
- Pause inference si batterie < 20%
- Mode "Eco" : modèles légers uniquement
- Dashboard : "Vous avez économisé X kg CO₂ vs. cloud"

---

### Intention #5 : Gratuité & Open Source
> "Tout cela gratuitement, sans que ce soit vous le produit"

**Stories alignées :**
- ✅ Toutes les stories utilisent outils open-source
- ✅ AITAO-007 (DuckDuckGo = pas de tracking)
- ✅ AITAO-018 (Metrics locales, jamais envoyées)

**Gaps :**
- ⚠️ Pas de story sur "Donation/Sponsorship UI" (si tu veux commercialiser)
- ⚠️ Pas de story sur "License Check" (vérifier dépendances open-source)

**Recommandation :**
BACKLOG OK. Pour commercialisation, ajouter Phase 4 :
- **AITAO-022 : Pro Version Features** (encryption, priority support)
- Dual license : Free (GPL) + Pro (Commercial)

---

## 🚨 Incohérences Détectées

### ❌ Incohérence #1 : Vision/Audio avant Web Search UI
**Problème :**
- AITAO-010 (Vision) et AITAO-012 (Audio) sont Phase 2
- AITAO-007 (Web Search UI) aussi Phase 2
- **Mais** : Web search backend déjà codé, vision/audio non

**Impact :**
- Quick win (web search) traité comme égal à features complexes

**Correction :**
Déplacer **AITAO-007 en Phase 1** (avec stories critiques) car :
1. Backend déjà fait (`web.py`)
2. Juste besoin UI toggle (2-3 points)
3. Débloque UC-003 immédiatement

---

### ⚠️ Incohérence #2 : Pas de story pour config.toml.template → config.toml
**Problème :**
- PRD dit : "config.toml = source de vérité"
- Mais actuellement : `config.toml.template` existe, utilisateur doit copier manuellement
- AITAO-004 (CLI) inclut `check config` mais pas "create config"

**Impact :**
- Utilisateur bloqué au premier lancement si pas technique

**Correction :**
Ajouter dans **AITAO-004** :
```bash
./aitao.sh init  # Génère config.toml interactivement
```

---

### ⚠️ Incohérence #3 : Benchmarks sans objectifs de performance
**Problème :**
- AITAO-009 (Benchmark) prévoit de mesurer performance
- Mais PRD dit : "Latency Target: To be defined based on user testing"
- Aucune story pour **définir** les targets

**Impact :**
- On mesure sans savoir si c'est "bon" ou "mauvais"

**Correction :**
Avant AITAO-009, ajouter **AITAO-008B : Define Performance SLA**
- User survey : "Combien de temps acceptable pour indexer 10GB ?"
- Définir targets : Query <3s, Indexing >1GB/min, etc.

---

## ✅ Stories Bien Alignées (À Conserver)

### Top 5 Stories Parfaitement Alignées :

1. **AITAO-001** (Logger PathManager)
   - ✅ Sert confidentialité (logs locaux)
   - ✅ Bloquant V1 (bug actuel)
   - ✅ Quick fix (2 points)

2. **AITAO-006** (Sync Agent)
   - ✅ Sert simplicité (auto-config UI)
   - ✅ Coeur du workflow
   - ✅ Déjà en cours de dev

3. **AITAO-015** (Watch Folders)
   - ✅ Sert simplicité radicale (drop & forget)
   - ✅ Cas d'usage direct
   - ✅ Value ajoutée vs. Spotlight

4. **AITAO-017** (Zero-Config Installer)
   - ✅ Sert accessibilité ("15 min setup")
   - ✅ Bloque adoption masse
   - ✅ Aligné roadmap Phase 4

5. **AITAO-003** (SHA-256 Hash)
   - ✅ Sert environnement (économie ressources)
   - ✅ Sert performance (skip unchanged)
   - ✅ Foundation pour scale

---

## 📝 Recommandations Finales

### Actions Immédiates (Sprint Actuel)

1. **Reséquencer Phase 1 :**
   ```
   Phase 1 (Actuel) :
   - AITAO-001 (Logger)
   - AITAO-002 (PathManager imports)
   - AITAO-003 (Hash)
   - AITAO-004 (CLI + init command)
   - AITAO-006 (Sync Agent)
   - AITAO-008 (E2E Test)
   + AITAO-007 (Web Search UI) ← AJOUTER (quick win)
   + AITAO-019 (Legacy cleanup) ← AJOUTER (1 point)
   ```

2. **Créer stories manquantes :**
   - **AITAO-020 :** First-Run Experience (onboarding)
   - **AITAO-008B :** Define Performance SLA (avant benchmarks)

3. **Clarifier estimations :**
   - AITAO-007 devrait être **2 points** (backend done), pas 3
   - AITAO-017 (Installer) est sous-estimé : **21 points** (Epic), pas 13

### Cohérence Globale

| Critère | Score | Commentaire |
|---------|-------|-------------|
| **Alignment Intentions** | 9/10 | 18/19 stories alignées, gaps mineurs |
| **Priorisation** | 8/10 | Web search sous-priorisé, sinon cohérent |
| **Séquençage** | 8/10 | Phase 1 solide, Phase 2+ à affiner |
| **Estimations** | 7/10 | Quelques epics sous-estimés |
| **Coverage** | 9/10 | Couvre bien V1, gaps en UX/Onboarding |

**Score Global : 8.2/10** ✅

---

## 🎯 Backlog Révisé - Proposition

### Phase 1 : Foundation (Sprint 1-3, ~25 points)
**Objectif :** Système stable, CLI complet, RAG fonctionnel

- AITAO-001 : Logger (2 pts) 🔥
- AITAO-002 : PathManager (2 pts) 🔥
- AITAO-003 : Hash (2 pts) 🔥
- AITAO-004 : CLI complet (3 pts) 🔥
- AITAO-006 : Sync Agent (5 pts) 🔥
- AITAO-007 : Web Search UI (2 pts) 🚀 ← DÉPLACÉ DE PHASE 2
- AITAO-008 : E2E Test (2 pts) 🔥
- AITAO-019 : Legacy cleanup (1 pt) 🧹
- AITAO-020 : First-Run UX (3 pts) 🚀 ← NOUVEAU
- AITAO-005 : Presentations (.pptx/.odp) (2 pts) 🚀

**Total Phase 1 : 24 points**

### Phase 2 : Core Features (Sprint 4-6, ~20 points)
**Objectif :** Vision, modèles multiples, watch folders

- AITAO-008B : Define SLA (1 pt) 🚀 ← NOUVEAU
- AITAO-009 : Benchmark (2 pts) 🚀
- AITAO-010 : Vision Model (8 pts) 🚀
- AITAO-011 : Code Model (5 pts) 🚀
- AITAO-015 : Watch Folders (5 pts) 🚀

**Total Phase 2 : 21 points**

### Phase 3 : Advanced (Sprint 7-9, ~18 points)
**Objectif :** Audio, SVG, intégrations

- AITAO-012 : Audio (5 pts) 🔮
- AITAO-013 : SVG Gen (8 pts) 🔮
- AITAO-014 : External API (3 pts) 🚀

**Total Phase 3 : 16 points**

### Phase 4 : Polish (Sprint 10+, ~40 points)
**Objectif :** Multi-plateforme, installer, métriques

- AITAO-016 : Multi-Platform (8 pts) 🛡️
- AITAO-017 : Zero-Config Installer (21 pts) 🛡️ ← RÉESTIMÉ
- AITAO-018 : Metrics Dashboard (5 pts) 🛡️

**Total Phase 4 : 34 points**

---

**Vélocité Estimée :** 8-10 points/sprint (1 sprint = 2 semaines)  
**V1 Launch :** Fin Phase 2 = ~10-12 semaines (Q1 2026)

---

*Document de validation - À discuter avec l'équipe*
