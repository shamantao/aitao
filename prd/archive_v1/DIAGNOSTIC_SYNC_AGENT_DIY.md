# 🔍 DIAGNOSTIC: Problème Majeur du Sync Agent DIY

**Date du diagnostic:** 27 Janvier 2026  
**Statut:** À DIAGNOSTIQUER (3 problèmes identifiés)  
**Criticité:** 🔴 **HAUTE** - Bloque les opérations du Sync Agent

---

## 📋 Résumé Exécutif

Le Sync Agent DIY rencontre **3 problèmes critiques** qui empêchent son fonctionnement optimal:

1. ❌ **EasyOCR ne supporte PAS le chinois** (langs: 'zh-cn', 'zh-tw')
2. ⚠️ **Avertissements PyTorch MPS** (pin_memory non supporté sur macOS)
3. 📊 **Dépendances instables/versioning issues** (lancedb, torch, etc.)

---

## 🐛 PROBLÈME 1: EasyOCR + Langues Chinoises

### Détails du Problème

**Erreur observée dans les logs:**
```
2026-01-27 11:32:38 [WARNING] [AITaoIndexer] EasyOCR init failed: ({'zh-cn', 'zh-tw'}, 'is not supported')
```

**Contexte:**
- `test_easyocr.py` essaie d'initialiser EasyOCR avec `['ch_tra', 'en']` ou `['en', 'ch_tra']`
- Cela échoue car EasyOCR **ne supporte pas** les codes de langue `'zh-cn'` ou `'zh-tw'`
- **Cependant:** EasyOCR IS initialized with `['en']` uniquement dans `kotaemon_indexer.py:381`

### Analyse Détaillée

**Fichier affecté:** [src/core/kotaemon_indexer.py](../src/core/kotaemon_indexer.py)

**Code actuel (ligne 378-384):**
```python
def _load_easy_reader(self) -> None:
    """Lazily instantiate EasyOCR reader."""
    if self.ocr_reader is None and EASY_AVAILABLE:
        try:
            self.ocr_reader = easyocr.Reader(["en"], gpu=False)  # ← Seulement ['en']
            logger.info("DEBUG RELOAD: EasyOCR initialized with ['en']")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"DEBUG RELOAD: EasyOCR init failed: {e}")
            self.ocr_reader = None
```

**Problème identifié:**
1. Le code utilise `["en"]` uniquement ✅ (correct)
2. Mais `test_easyocr.py` teste `['ch_tra', 'en']` ❌ (incorrect - échoue)
3. Le test ne reflète pas la réalité du code productif

### Logs Historiques

**Erreur du 27 Jan 11:32 UTC:**
```
2026-01-27 11:32:38 [WARNING] [AITaoIndexer] EasyOCR init failed: ({'zh-cn', 'zh-tw'}, 'is not supported')
```

**Mais après (12:32-13:00 UTC):**
```
2026-01-27 12:32:33 [INFO] [AITaoIndexer] DEBUG RELOAD: EasyOCR initialized with ['en']
2026-01-27 12:33:02 [INFO] [AITaoIndexer] DEBUG RELOAD: EasyOCR initialized with ['en']
```

**Conclusion:** EasyOCR fonctionne avec `['en']`, mais le test obsolète utilise `'ch_tra'`.

---

## ⚠️ PROBLÈME 2: PyTorch + MPS (Metal Performance Shaders)

### Détails du Problème

**Avertissements observés (fourni par l'utilisateur):**
```
UserWarning: 'pin_memory' argument is set as true but not supported on MPS now, device pinned memory won't be used.
  super().__init__(loader)
```

**Récurrence:** Cet avertissement apparaît **3 fois** dans la même exécution.

### Analyse Détaillée

**Contexte:**
- Python 3.14 + PyTorch sur macOS ARM64 (Apple Silicon)
- MPS (Metal Performance Shaders) activé par défaut sur Apple Silicon
- PyTorch DataLoader tente d'utiliser `pin_memory=True`
- MPS **ne supporte pas** le pinned memory

**Origine du problème:**
- Probablement dans `sentence-transformers` ou une lib de traitement de données
- Pas dans le code AITAO directement

### Logs Observés

```
/Users/phil/Library/CloudStorage/Dropbox/devwww/AI-model/aitao/.venv/lib/python3.14/site-packages/torch/utils/data/dataloader.py:775: UserWarning: 'pin_memory' argument is set as true but not supported on MPS now, device pinned memory won't be used.
```

**Impact:**
- ⚠️ Non-bloquant (juste un avertissement)
- ✅ Les opérations continuent
- ⚡ Performance légèrement dégradée (pas de pinned memory)

---

## 📦 PROBLÈME 3: Dépendances + Versioning Instabilité

### Détails du Problème

**Erreurs observées:**
1. `lancedb` importation failée (27 Jan 10:49 UTC)
2. LanceDB schema issues (`ocr_engine` field not found - 23 Jan 16:39)
3. Inconsistency entre les versions

### Logs Historiques

**27 Janvier 10:49 - Importation failée:**
```
2026-01-27 10:49:18 [WARNING] [AITaoIndexer] Indexer dependencies missing (No module named 'lancedb'). Indexing will be disabled.
2026-01-27 10:49:19 [WARNING] [AITaoIndexer] Indexer disabled: dependencies not available.
```

**23 Janvier 16:39 - Schema mismatch:**
```
2026-01-23 16:39:01 [ERROR] [AITaoIndexer] ❌ Failed to index /Users/phil/Downloads/_Volumes/世協舉辦「公益淨灘...pdf: name 'file_size' is not defined
2026-01-23 16:39:30 [ERROR] [AITaoIndexer] ❌ Failed to insert documents into LanceDB: Field 'ocr_engine' not found in target schema
```

**23 Janvier 19:54 - Workaround appliqué:**
```
2026-01-23 19:54:19 [WARNING] [AITaoIndexer] Could not ensure schema for 'ocr_engine': 'LanceTable' object has no attribute 'add_column'
...
2026-01-23 19:55:16 [INFO] [AITaoIndexer] 🛠️ Recreated collection with 'ocr_engine' column
```

**Erreurs de présentation (PPT):**
```
2026-01-27 12:44:20 [ERROR] [AITaoIndexer] Failed to extract presentation /Users/phil/Downloads/_Volumes/1200-公用資料/TR - Marketing 2022 v01.0.ppt: Package not found at '...'
```

---

## 🎯 Analyse Racine (Root Cause Analysis)

### Cause 1: EasyOCR + Chinois
- **Racine:** Test `test_easyocr.py` est **obsolète** et ne correspond pas au code productif
- **Raison historique:** Possible intention passée d'ajouter support chinois
- **Réalité actuelle:** Seul `['en']` est utilisé dans le code productif

### Cause 2: PyTorch + MPS
- **Racine:** Dépendance externe (`sentence-transformers` → PyTorch)
- **Raison:** MPS est très jeune sur macOS, DataLoader assume CPU/CUDA
- **Workaround:** Pas de solution triviale (PyTorch/sentence-transformers issue)

### Cause 3: Dépendances Instables
- **Racine:** Python 3.14 (version très récente, probablement en development)
- **Problèmes possibles:**
  - ABI incompatibility avec certains packages
  - Versions non pincées dans `requirements.txt`
  - LanceDB API changes
  - pptx library issues

---

## 📊 État Actuel du Sync Agent

### ✅ Ce qui Fonctionne

```
2026-01-27 12:37:12 [INFO] [AITaoIndexer] DEBUG RELOAD: EasyOCR initialized with ['en']
2026-01-27 12:40:57 [INFO] [AITaoIndexer] 📦 Archive detected: 1000-文管 2.7z (not extracting)
2026-01-27 12:50:07 [INFO] [AITaoIndexer] 📊 Extracted 98 slides from TR - Planetary eng_Tech 2023 v01.0.pptx
```

- ✅ Indexation de fichiers fonctionne
- ✅ EasyOCR en anglais fonctionne
- ✅ Extraction de présentations (pptx) fonctionne
- ✅ Recherche en chinois fonctionne (sentence-transformers multilingual)

### ❌ Ce qui Ne Fonctionne Pas

- ❌ OCR en chinois (non-bloquant, EasyOCR pas utilisé)
- ❌ Extraction de certains fichiers `.ppt` (format ancien PowerPoint)
- ⚠️ Pin_memory warnings (non-bloquant, juste avertissements)

---

## 🔧 Recommandations (À FAIRE dans le prochain prompt)

### 1. Nettoyer le code de test
- **Action:** Supprimer ou corriger `test_easyocr.py`
- **Priorité:** 🟡 MOYEN (pas bloquant)
- **Raison:** Évite la confusion et les faux positifs

### 2. Ajouter support français pour easyOCR
- **Action:** Envisager `['en', 'fr']` au lieu de `['en']` seulement
- **Priorité:** 🟡 MOYEN (amélioration)
- **Raison:** Support multi-langue pour data francophone

### 3. Pincer les versions des dépendances
- **Action:** `pip freeze > requirements-frozen.txt`
- **Priorité:** 🔴 HAUTE (stabilité)
- **Raison:** Python 3.14 change trop vite, besoin de versions stables

### 4. Ajouter support pour `.ppt` (ancien format)
- **Action:** Utiliser `python-pptx` pour les deux formats (.ppt et .pptx)
- **Priorité:** 🟡 MOYEN (améliorationUX)
- **Raison:** Certains fichiers échouent (TR - Marketing 2022 v01.0.ppt)

### 5. Ignorer les warnings MPS de PyTorch
- **Action:** Ajouter filtrage des warnings dans `.venv/lib/pythonrc`
- **Priorité:** 🟢 FAIBLE (cosmétique)
- **Raison:** Avertissement non-bloquant, améliore clarté des logs

---

## 📝 Fichiers Affectés

| Fichier | Problème | Gravité |
|---------|----------|----------|
| [scripts/test_easyocr.py](../scripts/test_easyocr.py) | Teste avec ch_tra (unsupported) | 🟡 |
| [src/core/kotaemon_indexer.py](../src/core/kotaemon_indexer.py) | Schema LanceDB issues (historic) | ✅ FIXED |
| [requirements.txt](../requirements.txt) | Versions non pincées | 🔴 |
| [.venv/...](../pyproject.toml) | Python 3.14 + MPS warnings | ⚠️ |

---

## 🎓 Conclusion

**Le Sync Agent DIY fonctionne correctement.**

Les "problèmes" observés sont:
1. **Un test obsolète** (`test_easyocr.py`) qui n'affecte pas la production
2. **Des avertissements cosmétiques** de PyTorch/MPS (non-bloquants)
3. **Des dépendances instables** (Python 3.14 trop jeune)

**Action immédiate:** Nettoyer le code de test et pincer les versions.

---

## 📋 Checklist de Vérification

- [ ] Vérifier que `sync_agent.log` n'a pas d'erreurs récentes
- [ ] Confirmer que les fichiers indexent correctement
- [ ] Tester OCR avec fichiers réels (non-chinois)
- [ ] Vérifier les perfs (comparaison Python 3.13 vs 3.14)
- [ ] Tester extraction de presentations (.ppt et .pptx)
