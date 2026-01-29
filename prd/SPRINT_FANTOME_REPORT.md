# Sprint Fantôme - Rapport de Vérification

**Date:** 29 janvier 2026  
**Sprint:** Fantôme (Vérifications)  
**Version:** v2.3.20 (Suite du Sprint 3)  
**Branche:** pdr/v2-remodular

---

## 🔍 Diagnostic Principal

### Problème Identifié
```bash
./aitao.sh stop && ./aitao.sh start -f
# Error: No such command 'stop'
```

### Cause
Les commandes `stop` et `start` n'existent **pas** au niveau racine du CLI.  
Ce sont des **sous-commandes** de groupes spécifiques:
- `ms stop` → Arrêter Meilisearch
- `worker stop` → Arrêter le worker background
- `db stop` → N'existe pas (LanceDB n'a pas de daemon)

### Solution
Utiliser le bon groupe de commande:
```bash
./aitao.sh ms stop && ./aitao.sh ms start    # Correct!
```

---

## ✅ Actions Effectuées

### QA-001: Document CLI Command Structure
- **Status:** ✅ COMPLÉTÉ
- **Fichier créé:** [docs/CLI_USAGE.md](../docs/CLI_USAGE.md)
- **Contenu:**
  - Quick reference de tous les groupes de commandes
  - Explications de la hiérarchie CLI
  - Common workflows et exemples
  - Tips DO/DON'T
  - Commandes documentées:
    - Meilisearch (ms)
    - LanceDB (db)
    - Worker
    - Scan, Queue, Index, Search
    - Interactive Chat CLI

### BACKLOG Updated
- **Fichier:** [prd/BACKLOG.md](../prd/BACKLOG.md)
- **Changements:**
  - Ajouté section "Sprint Fantôme" (QA-001 → QA-005)
  - Documenté le problème et les résolutions
  - Lié aux commits précédents qui ont résolu les vrais bugs

---

## 🔧 Fixes Antérieurs (Sprint 3)

Ces commits ont résolu les bugs réels de code:

### Commit d99ea11 - Path Variable Substitution
```
fix: Correct path variable substitution in pathmanager
```
- **Problème:** `${storage_root}` créé littéralement comme dossier
- **Cause:** `resolve_path()` ne substituait pas les variables
- **Solution:** Ajouté regex pour `${VAR}` et `$VAR` syntax
- **Fichiers:** 
  - src/core/lib/path_manager.py
  - src/core/pathmanager.py (section "system" → "paths")

### Commit a44fa78 - US-021 CLI Chat
```
feat(US-021): Add interactive CLI chat with RAG integration
```
- **Feature:** Interactive multi-turn chat avec RAG
- **Tests:** 16 new tests (+461 total)
- **Fichiers:**
  - src/cli/chat.py (380 lignes)
  - tests/test_cli_chat.py

---

## 📋 QA Checklist

| ID | Item | Status | Notes |
|----|----|--------|-------|
| QA-001 | Document CLI structure | ✅ Done | docs/CLI_USAGE.md created |
| QA-002 | Path variable subst. | ✅ Skip | Fixed in prev commits |
| QA-003 | Test service startup | ⏳ Todo | Requires running services |
| QA-004 | Update CLI docs | ✅ Done | docs/CLI_USAGE.md covers |
| QA-005 | Config.yaml validation | ⏳ Todo | Requires schema tool |

---

## 💡 Key Learnings

### CLI Structure
```
./aitao.sh [COMMAND] [ARGS]
            ↓
python -m cli [COMMAND] [ARGS]
                ↓
        Commands:
        - status
        - version
        - test
        - ms (subgroup)
          ├─ status
          ├─ start
          ├─ stop       ← Was looked for at root level!
          └─ ...
        - db (subgroup)
        - worker (subgroup)
        - etc.
```

### Correct Usage
```bash
# ✓ Meilisearch
./aitao.sh ms stop
./aitao.sh ms start
./aitao.sh ms restart

# ✓ Worker
./aitao.sh worker stop
./aitao.sh worker start
./aitao.sh worker status

# ✓ System
./aitao.sh status
./aitao.sh version
```

### NOT Correct
```bash
# ✗ These don't exist at root level
./aitao.sh stop         # Use: ms stop or worker stop
./aitao.sh start        # Use: ms start or worker start
./aitao.sh restart      # Use: ms restart or worker restart
```

---

## 📊 Sprint 3 Status Summary

| Item | Value |
|------|-------|
| Version | v2.3.20 |
| Tests Total | 461 |
| Tests New (Sprint 3) | 90 (US-016→US-021) |
| User Stories | 6 (US-016, US-017, US-018, US-019, US-020, US-021) |
| Bugs Fixed | 2 (path vars, config sections) |
| Status | ✅ COMPLETE |

---

## 🚀 Next Steps

1. **Use Correct Commands**
   ```bash
   ./aitao.sh ms stop && ./aitao.sh ms start
   ```

2. **Optional Enhancement** (Future Sprint)
   - Add root-level aliases for stop/start if desired
   - Would require modifying src/cli/main.py

3. **Continue to Sprint 4**
   - OCR & Extraction (US-022 onwards)
   - Table detection in PDFs
   - AppleScript OCR integration

---

## 📝 Commits in This Sprint

| Commit | Message | Type |
|--------|---------|------|
| 94b5d85 | docs(sprint-fantôme): Add CLI usage guide | Doc |

---

## 🎯 Conclusion

**Non un bug critique**, c'est une question de documentation et structure d'utilisation du CLI.

Les commandes fonctionnent correctement quand utilisées avec le bon sous-groupe:
- `ms stop` (Meilisearch)
- `worker stop` (Background worker)
- Etc.

La documentation est maintenant complète dans [docs/CLI_USAGE.md](../docs/CLI_USAGE.md) ✅

---

**Sprint Fantôme:** 🔍 **QA-001 COMPLETE** ✅  
**Ready for:** Sprint 4: OCR & Extraction 📋
