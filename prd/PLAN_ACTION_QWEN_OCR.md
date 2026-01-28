# 🎯 PLAN D'ACTION: OCR + Qwen-VL + Python 3.14

**Décision:** On GARDE Qwen-VL mais on le fait fonctionner correctement  
**Timeline:** 1-2 jours pour avoir une baseline fiable  
**Objectif:** Indexation fiable chinois + tableaux, performance connue

---

## 1️⃣ PHASE 1: DIAGNOSTIC COMPLET (2 heures)

### 1.1: Tester Qwen-VL Réellement

**Script à créer:** `scripts/test_qwen_ocr.py`
```python
#!/usr/bin/env python3
"""
Test Qwen-VL OCR réel sur le volume de test.
Mesure:
- Chargement du modèle
- Temps par image
- Qualité extraction (chinois + tableaux)
- Comparaison EasyOCR vs Qwen-VL
"""
```

**Fichiers de test:**
- 3-5 fichiers chinois (PDF scanned)
- 3-5 images avec tableaux
- 3-5 images anglaises simples
- 3-5 PDFs natifs chinois

**Mesures à prendre:**
- ⏱️ Temps de chargement modèle
- ⏱️ Temps par fichier (EasyOCR vs Qwen)
- ✅ Qualité texte (human eval: Est-ce lisible? Complet?)
- ✅ Tableaux (EasyOCR les manque-t-il? Qwen les capture-t-il?)
- 🐏 Mémoire utilisée

### 1.2: Vérifier Historique EasyOCR + Chinois

**Questions à répondre:**
1. ✅ Config originale avait-elle `['ch_tra', 'en']`? (dans un ancien script?)
2. ✅ Pourquoi retiré? ("ne détectait rien" = pas d'OCR du tout, ou mauvais résultat?)
3. ✅ A-t-on testé si `['zh_sim', 'en']` marcherait mieux?

**Où chercher:**
- Git history si dispo
- `prd/` pour voir si mentionné
- `scripts/` pour voir test ancien

### 1.3: Reproduire le Problème

**Test simple:**
```bash
# Vérifier que EasyOCR ne supporte PAS le chinois
python -c "
import easyocr
try:
    reader = easyocr.Reader(['zh-cn'], gpu=False)
    print('✅ zh-cn works')
except Exception as e:
    print(f'❌ zh-cn fails: {e}')
"
```

---

## 2️⃣ PHASE 2: FIXER LA DÉTECTION DE TABLEAUX (1 heure)

### Problème Actuel

Code demande ALL of:
- `rel_area >= 0.15` (15% du contenu = lignes)
- `intersections >= 4` (au moins 4 intersections de grid)
- `density >= 0.0005` (densité lignes haute)

**Résultat:** Presque jamais True → Toujours EasyOCR

### Solution: Strategie Pragmatique

**Option A: Simple - Baisser les seuils** (Quick fix)
```python
# Make table detection less aggressive
if (rel_area >= 0.05    # Baisser de 0.15 à 0.05 (5%)
    and intersections >= 2  # Baisser de 4 à 2
    and density >= 0.0002):  # Baisser de 0.0005 à 0.0002
    return "qwen"
```

**Option B: Intelligent - Utiliser Qwen si pas certain**
```python
# Si conditions 60% vraies → utiliser Qwen (safer)
def _choose_engine(self, fp: Path) -> str:
    mode = self.ocr_config.get("engine", "auto").lower()
    if mode in {"easyocr", "qwen"}:
        return mode

    # Table detection: si doute, préférer Qwen
    has_table = False
    if CV_AVAILABLE:
        try:
            rel_area, intersections, density = self._detect_table_stats(fp)
            # More lenient: au moins 2 des 3 conditions
            condition_count = sum([
                rel_area >= 0.05,
                intersections >= 2,
                density >= 0.0002
            ])
            has_table = condition_count >= 2
        except:
            pass
    
    return "qwen" if has_table else "easyocr"
```

**Option C: Config-based** (Cleanest)
```toml
[ocr]
engine = "auto"  # ou "easyocr", "qwen"
table_area_min = 0.05      # Make it configurable
min_intersections = 2
min_line_density = 0.0002

# NEW: Pour forcer test
test_mode = false          # Si true, utiliser Qwen pour TOUT
```

### Recommandation: Faire Option B + Config

- Baisse les seuils logiquement
- Ajoute la logique "au moins 2 conditions"
- Permet config TOML pour ajustements
- Permet un mode test `engine = "qwen"` pour forcer test

---

## 3️⃣ PHASE 3: RÉSOUDRE PYTHON 3.14 (1-2 heures)

### Problème 1: Pin_Memory MPS Warning

**Symptôme:**
```
UserWarning: 'pin_memory' argument is set as true but not supported on MPS now
```

**Cause:** PyTorch DataLoader assume CPU/CUDA, pas MPS

**Solution 1: Silence les warnings** (Quick)
```python
# Dans kotaemon_indexer.py au démarrage
import warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")
```

**Solution 2: Fix root** (Better)
```python
# Dans sentence-transformers usage
# Check if on macOS + disable pin_memory
import torch
is_mps = torch.backends.mps.is_available()
pin_memory = not is_mps  # Don't pin on MPS
```

### Problème 2: Dépendances Instables

**Vérifier compatibilité Python 3.14:**
```bash
pip list | grep -E "torch|sentence|lancedb|easyocr"
```

**Pin versions robustes:** Créer `requirements-stable.txt`
```txt
# Python 3.14 tested versions
torch==2.4.1          # Tested on 3.14
sentence-transformers==2.7.0
lancedb==0.8.2
easyocr==1.7.1
opencv-python==4.10.1
pdf2image==1.17.0
pdfminer.six==20240706
python-pptx>=0.6.23
Pillow>=10.2.0
watchfiles>=1.0.0
toml>=0.10.2
```

**Tester pour voir warnings/errors:**
```bash
python scripts/test_core_services.sh
```

### Problème 3: Version Homebrew Python

Tu ne peux pas "downgrade" Homebrew Python. Solutions:

**Option A: Use venv avec Python alternatif**
```bash
# Si tu as Python 3.13 installé ailleurs
/path/to/python3.13 -m venv .venv-3.13
source .venv-3.13/bin/activate
pip install -r requirements-stable.txt
```

**Option B: Accepter 3.14 et fixer les warnings**
```bash
# Pin strict versions, filtrer warnings
pip install --force-reinstall -r requirements-stable.txt
```

**Recommandation:** Option B (3.14 should work, just need right dependencies)

---

## 4️⃣ PHASE 4: TEST & BENCHMARK (1-2 heures)

### 4.1: Créer Suite de Test

**Répertoire:** `scripts/ocr_benchmark/`
```
scripts/ocr_benchmark/
├── test_data/
│   ├── chinese_pdf_scanned.pdf      # Chinois scanné
│   ├── chinese_pdf_native.pdf       # Chinois natif
│   ├── english_table.jpg            # Table anglaise
│   ├── chinese_table.jpg            # Table chinoise
│   └── simple_image.png             # Image simple
├── benchmark_easyocr.py              # Test EasyOCR uniquement
├── benchmark_qwen.py                 # Test Qwen uniquement
├── benchmark_compare.py              # Comparison + rapport
└── README.md                         # Instructions
```

### 4.2: Benchmark Script

```python
# benchmark_compare.py
"""
Compare EasyOCR vs Qwen-VL sur dataset réel.
Output: JSON report avec temps/qualité.
"""
import time, json
from pathlib import Path

def benchmark_easyocr(image_paths):
    """Run EasyOCR, measure time + quality"""
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False)
    
    results = []
    for img in image_paths:
        start = time.time()
        text = ...  # OCR
        elapsed = time.time() - start
        results.append({
            "file": img.name,
            "tool": "easyocr",
            "time_sec": elapsed,
            "char_count": len(text),
            "text_sample": text[:100]
        })
    return results

def benchmark_qwen(image_paths):
    """Run Qwen-VL, measure time + quality"""
    # Similar structure
    pass

# Generate report
report = {
    "easyocr": benchmark_easyocr(test_images),
    "qwen": benchmark_qwen(test_images),
    "summary": {
        "easyocr_avg_time": ...,
        "qwen_avg_time": ...,
        "recommendation": "Use Qwen if 2x slower but 80% better quality"
    }
}
print(json.dumps(report, indent=2))
```

---

## 5️⃣ PHASE 5: FIX FINAL (2-3 heures)

### 5.1: Mettre à Jour Indexer

Basé sur résultats du benchmark:

**Si Qwen-VL est bon:**
- ✅ Garder router intelligent
- ✅ Fixer table detection (Option B)
- ✅ Config TOML pour ajustements

**Si Qwen-VL est trop lent:**
- ✅ Garder EasyOCR en default
- ✅ Mode `engine = "qwen"` pour cas spéciaux
- ✅ Documenter quand l'utiliser

### 5.2: Mettre à Jour Config

```toml
[ocr]
# Engine: "auto" (smart routing), "easyocr" (fast, simple), "qwen" (best quality)
engine = "auto"

# Smart routing thresholds (si engine="auto")
table_area_min = 0.05
min_intersections = 2
min_line_density = 0.0002

# Qwen model (required if engine="qwen" or engine="auto")
qwen_model_path = "/Users/phil/Downloads/_sources/AI-models/qwen2-vl-7b/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"

# Benchmark results (for documentation)
benchmark_date = "2026-01-27"
easyocr_avg_time = "2.3 sec/image"
qwen_avg_time = "12.5 sec/image"
quality_easyocr = "Good for English, fails on Chinese OCR"
quality_qwen = "Excellent for tables and Chinese"
```

### 5.3: Documenter

**Créer:** `QWEN_VL_IMPLEMENTATION.md`
- Quand utiliser Qwen vs EasyOCR
- Performance (du benchmark)
- Configuration
- Troubleshooting

---

## 🎬 TIMELINE CONCRET

| Phase | Tâche | Temps | Status |
|-------|-------|-------|--------|
| 1 | Tester Qwen-VL réel | 1h | TODO |
| 1 | Historique EasyOCR+chinois | 30min | TODO |
| 2 | Fixer table detection | 45min | TODO |
| 3 | Python 3.14 warnings | 30min | TODO |
| 3 | Pin versions | 30min | TODO |
| 4 | Créer benchmark suite | 1h | TODO |
| 4 | Lancer benchmark | 1h | TODO |
| 5 | Fix final + update config | 1h | TODO |
| 5 | Documenter | 45min | TODO |
| — | **TOTAL** | **~7h** | — |

**Cible:** Demain matin avoir une version stable avec benchmark clair.

---

## ❓ QUESTIONS AVANT DE COMMENCER

1. **Qwen-VL model path est-il correct?**
   ```bash
   ls -lh /Users/phil/Downloads/_sources/AI-models/qwen2-vl-7b/
   ```
   → Doit être 4.8GB + fichier .gguf

2. **As-tu des images/PDFs chinois de test?**
   → A sélectionner dans `/Users/phil/Downloads/_Volumes/`

3. **Priorité: Speed ou Quality?**
   - Si speed: rester EasyOCR
   - Si quality: accepter Qwen (plus lent)
   - Si hybrid: router intelligent + seuils baisses

4. **Python 3.14 est critique ou flexible?**
   - Si flexible: créer venv Python 3.13
   - Si critique: fixer warnings et avancer

---

## ✅ CHECKLIST DÉBUT

- [ ] Qwen model path est accessible
- [ ] Au minimum 3 images de test chinoises disponibles
- [ ] Décision: Speed vs Quality vs Hybrid
- [ ] Décision: 3.14 ou alternative Python
- [ ] Créer branche feature: `feat/qwen-ocr-testing`

**À toi de jouer! Veux-tu commencer par Phase 1?**
