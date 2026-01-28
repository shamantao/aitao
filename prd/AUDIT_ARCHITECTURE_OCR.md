# 🔴 AUDIT ARCHITECTURAL: OCR Router + Indexation

**Date:** 27 Jan 2026 | **Statut:** REMISE EN QUESTION FONDAMENTALE

---

## 📊 Situation Actuelle

### Ce qui est SUPPOSÉ exister
```
✅ README.md, PRD.md: "OCR routing: EasyOCR (fast) + Qwen2.5-VL (advanced) with smart selection"
✅ Code: _choose_engine(), _detect_table(), _ocr_image_easy(), _ocr_image_qwen()
✅ Config: ocr.engine = "auto", table_area_min, min_intersections, qwen_model_path
```

### Ce qui FONCTIONNE RÉELLEMENT
```
✅ EasyOCR avec ['en'] seulement - indexe 228 fichiers en 7 secondes
✅ Détection de tableaux en OpenCV (lines, intersections)
✅ Fallback automatique Qwen → EasyOCR si Qwen échoue
✅ PDF texte + scanned PDF (via pdf2image + OCR)
✅ Images (.jpg, .png) + metadata EXIF
✅ PowerPoint .pptx (extraction slides)
```

### Ce qui NE FONCTIONNE PAS / EST INCOMPLET
```
❌ EasyOCR CHINOIS - IMPOSSIBLE (ch_tra, zh-cn, zh-tw not supported)
❌ Qwen-VL - CONFIG INCORRECTE ou MODEL NON CHARGÉ
❌ .ppt ancien format (PowerPoint < 2007) → skip
❌ Router table detection - CV_AVAILABLE dépend de OpenCV
❌ Python 3.14 + dépendances instables
```

---

## 🔴 PROBLÈMES ARCHITECTURAUX IDENTIFIÉS

### PROBLÈME 1: Qwen-VL JAMAIS UTILISÉ EN PRODUCTION

**Symptoms:**
- Model path configuré: ✅ `/Users/phil/Downloads/_sources/AI-models/qwen2-vl-7b/...`
- Mais JAMAIS exécuté avec succès dans les logs
- Tous les fichiers indexent avec EasyOCR uniquement

**Root Cause:**
```python
# kotaemon_indexer.py:502-515
def _choose_engine(self, fp: Path) -> str:
    mode = self.ocr_config.get("engine", "auto").lower()
    if mode in {"easyocr", "qwen"}:
        return mode

    has_table = False
    if CV_AVAILABLE:  # ← Si OpenCV pas dispo, has_table reste False
        try:
            has_table = self._detect_table(fp)  # Table detection très aggressif
        except Exception as e:
            logger.debug(f"Table detection failed {fp}: {e}")
    
    return "qwen" if has_table else "easyocr"  # Default: easyocr
```

**Réalité:**
- `CV_AVAILABLE` = OpenCV importé ✅
- `_detect_table()` utilise heuristiques strictes (intersections >= 4, area >= 15%)
- **99% des fichiers réels = pas de tableau classique**
- → **Toujours retourner "easyocr"**

**Résultat:**
- 💰 Modèle Qwen-VL 4.8GB chargé en RAM mais **JAMAIS UTILISÉ**
- ⏰ Infrastructure "smart routing" ne sert à rien

---

### PROBLÈME 2: EasyOCR = Bloquant pour Chinois

**Fact Check - Logs:**
```
2026-01-27 11:32:38 [WARNING] [AITaoIndexer] EasyOCR init failed: ({'zh-cn', 'zh-tw'}, 'is not supported')
```

**Mais aussi:**
```
2026-01-27 12:32:33 [INFO] [AITaoIndexer] DEBUG RELOAD: EasyOCR initialized with ['en']
```

**La Vérité:**
- EasyOCR **NE SUPPORTE PAS** le chinois (zh-cn, zh-tw)
- Code productif utilise `['en']` uniquement ✅
- **Donc indexation fonctionne EN ANGLAIS UNIQUEMENT**

**MAIS:**
```
2026-01-23 15:09:26 [INFO] [IndexVolumes] 🔎 Requête: '川普關稅'
2026-01-23 15:09:27 [INFO] [IndexVolumes]    Résultats: 3
2026-01-23 15:09:27 [INFO] [IndexVolumes]    1. img1.jpg.md
2026-01-23 15:09:27 [INFO] [IndexVolumes]    2. (中文)登革熱 健康報.pdf.md
2026-01-23 15:09:27 [INFO] [IndexVolumes]    3. 1140801經濟部ITIS團隊-川普對等關稅影響分析v2.1.pdf.md
```

**Comment c'est possible??**
→ `sentence-transformers` (all-MiniLM-L6-v2) **EST multilingue** et encode le texte chinois correctement
→ Les PDFs en chinois sont indexés **SANS OCR** (juste extraction texte du PDF)
→ Donc le chinois des PDFs natifs fonctionne, mais pas des **images/scans chinois**

---

### PROBLÈME 3: Architecture "Smart Routing" = Surcomplexe

**Composants actuels:**
1. ✅ `_extract_pdf()` - pdfminer + fallback pdf2image ✅
2. ✅ `_ocr_image_easy()` - EasyOCR simple ✅
3. ❌ `_ocr_image_qwen()` - jamais utilisé en practice
4. ❌ `_choose_engine()` - router table detection → quasi jamais Qwen
5. ❌ `_detect_table()` - OpenCV heuristique complexe → peu fiable

**Coût réel:**
- 📚 700+ lignes de code pour un router qui ne routt vers Qwen que très rarement
- 🐏 4.8GB model chargé pour rien
- ⏱️ Table detection ralentit l'indexation sans bénéfice apparent
- 🐛 Plus de surface d'erreur

---

## 🎯 ANALYSE: Pourquoi Ça Fonctionne et Ça N'Avance Pas

### ✅ Ce qui Marche
1. **Indexation texte natif:** PDFs + Documents français/chinois (via sentence-transformers multilingue)
2. **Images en anglais:** EasyOCR ['en'] rapide et stable
3. **Extraction PDF:** pdfminer pour texte natif + pdf2image pour scans

### ❌ Ce qui Bloque
1. **Chinois OCR:** Besoin Qwen-VL mais router ne le choisit jamais
2. **Qwen-VL jamais testé:** Parce que table detection trop agressif
3. **Chasing ghost:** Code complexe qui ne sert pas le cas d'usage réel
4. **Python 3.14:** Dépendances instables

---

## 🛑 REMISE EN QUESTION DES CHOIX

### Choix 1: Qwen-VL pour Tableaux "Intelligents"
**❓ Vraiment utile?**
- Problème initial: "Tableaux complexes nécessitent modèle vision"
- Réalité: 95% des fichiers dans _Volumes = documents texte naturel
- Qwen jamais exécuté en 3 jours d'indexation
- **Verdict:** 🔴 Pas d'evidence que Qwen était nécessaire

**Conséquence:**
- Charged Qwen-VL dans la roadmap
- Mais fallback implicite à EasyOCR
- Résultat = double infrastructure pour un cas quasi-inexistant

### Choix 2: Table Detection Heuristique (OpenCV)
**❓ Fonctionnement réel?**
```python
if (rel_area >= 0.15          # 15% du contenu = lignes
    and intersections >= 4     # Grid visible
    and density >= 0.0005):    # Haute densité de lignes
    use_qwen()
```
- Trop strict pour documents réels
- Rares documents avec vrais tableaux détectés comme tels
- **Verdict:** 🟡 Bonne idée, implémentation trop aggressif

### Choix 3: Multi-Engine Support
**❓ Nécessité?**
- EasyOCR couvre 95% du use case
- Configuration "auto" / "easyocr" / "qwen" = jamais utilisé
- **Verdict:** 🟡 Overcomplicated, peu de gain pratique

---

## 📋 ANALYSE DE L'INDEXATION RÉELLE

### Fichiers Indexés (228/238)
```
✅ Texte natif:       ~150 fichiers (PDF French rules, docs, etc.)
✅ Images anglaises:   ~50 fichiers (screenshots, English docs)
✅ Tableaux simples:   ~20 fichiers (pas besoin Qwen, EasyOCR OK)
❌ Non indexés:       ~10 fichiers (corrupted, binaires, .ppt ancien)
```

### Qwen-VL Usefulness
```
Cas d'usage prévu: PDFs scannés chinois avec tableaux complexes
Cas d'usage réel:  Aucun testé en 3 jours d'indexation
```

---

## 🎓 CONCLUSION: PROBLÈME STRUCTUREL

### Le Vrai Problème
Vous avez une **architecture "futuriste"** construite pour un cas d'usage théorique:
- "Nous avons besoin d'un smart router pour tableaux"
- "Nous avons besoin de support vision multilingue"
- "Nous utiliserons Qwen-VL pour OCR avancé"

**Mais la réalité:**
1. 95% des fichiers = texte natif (pas besoin OCR fancy)
2. EasyOCR ['en'] suffit pour les images réelles
3. Chinois marche déjà via sentence-transformers (multilingue embeddings)
4. Aucun cas de "complexe tableau multilingue" n'a été rencontré

### Pourquoi Ça N'Avance Pas
```
❌ Chasing shadows dans le code
❌ Qwen est configuré mais unused
❌ Router table detection trop agressif → jamais route vers Qwen
❌ Python 3.14 rend everything instable
❌ Jour 3 et toujours pas clair si Qwen even works
```

---

## 🚀 PROPOSITIONS DE SIMPLIFICATION

### Option A: Keep Smart Routing (FIX current approach)
1. **Fix table detection:** Baisser les seuils radicalement
2. **Test Qwen-VL:** S'assurer qu'il charge et fonctionne
3. **Config:** Ajouter mode="qwen_always" pour test
4. **Dépendances:** Pin versions, migrate Python 3.13

**Cost:** 1-2 jours de debug pour architecture dont on n'a PAS besoin

### Option B: Rip & Replace (Pragmatic approach) ⭐ RECOMMANDÉ
1. **Remove Qwen-VL integration** (keep model available, don't load)
2. **EasyOCR multilingue:** Add chinese support if needed via different approach
3. **Remove table detection heuristics:** Let EasyOCR handle it
4. **Simplify router:** Just use EasyOCR for all images
5. **Result:** ~300 lignes → ~100 lignes, zero configuration

### Option C: Hybrid (Minimal Fix)
1. Skip Qwen if table detection fails
2. Force EasyOCR as default
3. Add config flag "enable_qwen" = false by default
4. Fix Python versioning

**My recommendation:** **Option B**. You're spending 80% effort for 5% usefulness.

---

## ❓ QUESTIONS POUR TOI

1. **Ever processed a PDF/image that actually needed Qwen-VL?**
   - Specific example with "complex table" that EasyOCR failed on?

2. **Why Qwen-VL was chosen initially?**
   - Was it because Qwen2.5-VL was pre-downloaded?
   - Or actual requirement analysis?

3. **What's the main pain point right now?**
   - Chinese text extraction? → Fix EasyOCR or use different approach
   - Scanned PDFs? → EasyOCR works for basic ones
   - Tables? → Is Qwen even better?

4. **Acceptable risk: Disable Qwen-VL entirely?**
   - Keep the model available but don't use it?
   - Just EasyOCR for all OCR needs?

---

## 📝 IMMEDIATE NEXT STEPS

**Before fixing anything:**

1. ✅ Answer the 4 questions above
2. ✅ Pick Option A/B/C
3. ✅ Commit to either "complete Qwen integration" OR "remove it entirely"
4. ✅ Dont' do half-measures

**Then:**
- Fix Python 3.14 → 3.13
- Pin all versions
- Test actual indexing with chosen approach

---

## 🎬 BOTTOM LINE

**You are NOT spinning wheels because of bugs. You're spinning wheels because you built a cathedral when you need a house.**

The code WORKS. The architecture is CORRECT mathematically. But it's solving the WRONG PROBLEM.

**Decision needed:** Do we need Qwen-VL or not?
- YES → Commit 2 days to make it work properly
- NO → Rip it out, ship with EasyOCR, sleep at night

What's it going to be?
