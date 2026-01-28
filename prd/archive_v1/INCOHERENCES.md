# AI Tao - Analyse des Incohérences & Recommandations

**Date d'analyse:** 22 janvier 2026  
**Contexte:** Audit du code existant vs. intentions du PRD

---

## 🔍 Incohérences Détectées

### 1. Logger non centralisé (🔥 Critique)

**État actuel:**
- `logger.py` existe avec `get_logger(name)` qui crée des handlers
- **Problème:** Hardcode le nom de fichier `web_search.log` (ligne 36)
- Utilise `path_manager.get_logs_dir()` MAIS seulement pour web_search

**Fichier concerné:**
```python
# src/core/logger.py:36
log_file = logs_dir / "web_search.log"  # ❌ Hardcodé !
```

**Impact:**
- Tous les logs vont dans le même fichier au lieu d'être séparés (api.log, sync.log, etc.)
- Pas de centralisation selon l'intention du PRD

**Recommandation:**
```python
def get_logger(name, log_filename=None):
    """
    Get configured logger for a module.
    
    Args:
        name: Logger name (module path)
        log_filename: Optional filename (defaults to f"{name}.log")
    """
    if log_filename is None:
        # Extract last part of module name: src.core.web → web.log
        log_filename = f"{name.split('.')[-1]}.log"
    
    logs_dir = path_manager.get_logs_dir()
    log_file = logs_dir / log_filename
    # ... rest
```

**Tâches:**
- ✅ Créer AITAO-001 dans le backlog
- Modifier `logger.py` pour accepter `log_filename`
- Mettre à jour tous les appels: `get_logger("web_search", "web_search.log")`

---

### 2. Architecture PathManager (✅ Correcte - Pas une incohérence)

**État actuel:**
- `src/core/lib/path_manager.py` = **Classe générique réutilisable** (`GenericPathManager`)
- `src/core/aitao_configpath.py` = **Implémentation spécifique AItao** (hérite de Generic)
- `src/core/path_manager.py` = **Shim pour compatibilité** (facilite les imports)

**Architecture:**
```python
# src/core/lib/path_manager.py
class GenericPathManager:  # ✅ Base réutilisable
    """Reusable for any project"""

# src/core/aitao_configpath.py  
class AitaoPathManager(GenericPathManager):  # ✅ Spécifique projet
    """Aitao-specific logic (storage_root, logs, models)"""

# src/core/path_manager.py (shim)
from src.core.aitao_configpath import path_manager  # ✅ Clean import
```

**Verdict:**
✅ **C'est du bon design** - Séparation générique/spécifique, réutilisabilité.  
❌ **Pas une incohérence**, c'est une bonne pratique.

**Impact:**
- Architecture saine pour évolution (ex: réutiliser Generic dans autre projet)
- Le shim `path_manager.py` simplifie les imports partout

**Recommandation:**
- ✅ **Garder le shim** (ne pas supprimer)
- ✅ Documenter l'architecture dans docstrings
- Juste s'assurer que tous les modules l'utilisent

**Tâches:**
- ✅ Mettre à jour AITAO-002 dans le backlog (compris maintenant)
- ❌ Annuler DEBT-001 (le shim n'est pas une dette)

---

### 3. Métadonnées incomplètes dans l'indexer (🚀 Haute priorité)

**État actuel:**
- `indexer.py` extrait seulement: `source`, `filename`, `type`
- **Manquant:** hash SHA-256 (demandé par utilisateur)

**Code actuel:**
```python
# src/core/indexer.py:93
batch_items.append({
    "text": chunk,
    "metadata": {
        "source": rel_path,
        "filename": os.path.basename(file_path),
        "type": "code" if file_path.endswith(('.py', '.js', '.sh')) else "doc"
    }
})
```

**Intention du PRD:**
> "Metadata extraction: File paths, modification dates, **SHA-256 hash (integrity)**, content summaries"

**Impact:**
- Pas de détection de changements (re-indexe tout à chaque scan)
- Gaspillage de ressources CPU/RAM

**Recommandation:**
```python
import hashlib

def compute_file_hash(file_path):
    """Compute SHA-256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"

# Dans index_directory_generator():
file_hash = compute_file_hash(file_path)

# Avant d'indexer, vérifier si hash existe déjà dans DB
existing = rag.get_by_source_and_hash(rel_path, file_hash)
if existing:
    yield "status", f"⏭️  Skipping {rel_path} (unchanged)"
    continue

# Ajouter au metadata
metadata = {
    "source": rel_path,
    "filename": os.path.basename(file_path),
    "type": "code" if file_path.endswith(('.py', '.js', '.sh')) else "doc",
    "hash": file_hash,  # ✅ Ajout
    "mtime": os.path.getmtime(file_path)
}
```

**Tâches:**
- ✅ Créer AITAO-003 dans le backlog
- Implémenter fonction `compute_file_hash()`
- Ajouter méthode `rag.get_by_source_and_hash()` dans `rag.py`
- Tester avec 1000 fichiers: vérifier que 2e scan skip les inchangés

---

### 4. Types de fichiers manquants (🚀 Haute priorité)

**État actuel:**
```python
# src/core/indexer.py:41
SUPPORTED_EXTENSIONS = {
    '.md', '.txt', '.py', '.sh', '.json', 
    '.html', '.js', '.ts', '.css', '.mdx', '.rst'
}
```

**Intention PRD:**
> Documents: .txt, .md, .docx, .odt  
> **Presentations: .odp, .pptx**  ← Manquant !

**Impact:**
- Utilisateurs ne peuvent pas indexer leurs présentations
- Cas d'usage bloqué (recherche dans slides)

**Recommandation:**
```python
SUPPORTED_EXTENSIONS = {
    # Documents
    '.md', '.txt', '.docx', '.odt',
    # Presentations
    '.odp', '.pptx',
    # Code
    '.py', '.sh', '.js', '.ts', '.json', '.css',
    # Markup
    '.html', '.xml', '.mdx', '.rst'
}
```

**Dépendances:**
- `python-pptx` pour .pptx
- `odfpy` pour .odp

**Tâches:**
- ✅ Créer AITAO-005 dans le backlog
- Rechercher meilleures librairies open-source
- Implémenter extraction de texte (slides + notes)
- Ajouter à `requirements.txt`

---

### 5. Recherche web déjà implémentée mais non intégrée (✅ Partiellement fait)

**État actuel:**
- ✅ `web.py` contient `search_ddg_html()` fonctionnel
- ✅ Utilise DuckDuckGo (privacy-friendly)
- ❌ Pas exposé dans l'interface AnythingLLM
- ❌ Pas de toggle "🌐 Web Search" dans le chat

**Code existant:**
```python
# src/core/web.py:71
def search_ddg_html(query: str, max_results=10) -> list:
    """Fallback Manuel : Scrape html.duckduckgo.com."""
    # ... implémentation complète ✅
```

**PRD Status:**
> FR-004: Web Search (Opt-in) - Status: 📋 TODO

**Correction PRD:**
> Status: ✅ Core Implementation Done (DuckDuckGo scraper), UI Integration TODO

**Impact:**
- Fonctionnalité déjà codée mais invisible pour l'utilisateur
- Quick win: juste l'intégrer à l'UI

**Recommandation:**
1. Exposer endpoint API: `POST /v1/search/web`
2. Modifier AnythingLLM workspace settings: ajouter checkbox "Enable Web Search"
3. Injecter résultats dans contexte LLM avec format Perplexity

**Tâches:**
- ✅ Créer AITAO-007 dans le backlog
- ✅ Corriger statut dans PRD
- Implémenter endpoint dans `server.py`
- Documenter usage

---

### 6. Modèles téléchargés hors du projet (⚠️ Architecture)

**État actuel:**
- 3 modèles téléchargés dans `_sources/AI-models/`
- Pas dans le répertoire du projet `aitao/`
- `config.toml.template` pointe vers `/path/to/your/models` (placeholder)

**Modèles disponibles:**
```
_sources/AI-models/
├── llama3.1-8b/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
├── Qwen-2.5-Coder/qwen2.5-coder-7b-instruct-q4_k_m.gguf
└── qwen2-vl-7b/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
```

**Intention PRD:**
> FR-006: Vision Capabilities - Status: 📋 TODO

**Correction PRD:**
> Status: 🔄 Models Downloaded, Integration TODO

**Impact:**
- Modèles prêts mais non utilisés
- Configuration utilisateur manquante (quel chemin pointer ?)

**Recommandation:**
1. **Option A (Recommandée):** Créer symlink dans projet
   ```bash
   ln -s /Users/phil/Downloads/_sources/AI-models aitao/models
   ```

2. **Option B:** Copier modèles dans `aitao/data/models/`

3. **Option C:** Garder séparé mais documenter dans setup

**Config à mettre à jour:**
```toml
[models]
models_dir = "/Users/phil/Downloads/_sources/AI-models"

# Définir les modèles disponibles
[[models.profiles]]
name = "llama3.1-8b"
path = "llama3.1-8b/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
type = "text"
context_size = 8192

[[models.profiles]]
name = "qwen-coder"
path = "Qwen-2.5-Coder/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
type = "code"
context_size = 8192

[[models.profiles]]
name = "qwen-vision"
path = "qwen2-vl-7b/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
type = "vision"
context_size = 4096
```

**Tâches:**
- Décider approche (A/B/C) avec utilisateur
- Mettre à jour `config.toml.template`
- ✅ Corriger statut dans PRD (AITAO-010, AITAO-011)
- Créer `scripts/setup_models.sh` pour automatiser

---

### 7. CLI incomplet (🚀 Haute priorité)

**État actuel:**
```bash
# aitao.sh commands implemented:
✅ start
✅ stop
✅ status

# Missing (per PRD FR-002):
❌ restart
❌ check [scan|config]
❌ help
```

**Intention PRD:**
> FR-002: CLI Interface - All commands functional

**Impact:**
- Utilisateur doit faire `./aitao.sh stop && ./aitao.sh start` manuellement
- Pas de validation de config avant démarrage (erreurs au runtime)

**Recommandation:**
```bash
# Ajouter dans aitao.sh:

restart() {
    echo -e "${BLUE}🔄 Redémarrage d'AI Tao...${NC}"
    stop_all
    sleep 2
    start_all
}

check_config() {
    echo -e "${BLUE}🔍 Validation de $CONFIG_FILE...${NC}"
    $PYTHON -c "
import toml
try:
    config = toml.load('$CONFIG_FILE')
    print('✅ Syntaxe TOML valide')
    print(f'Storage Root: {config[\"system\"][\"storage_root\"]}')
    print(f'Models Dir: {config[\"models\"][\"models_dir\"]}')
except Exception as e:
    print(f'❌ Erreur: {e}')
    exit(1)
"
}

check_scan() {
    echo -e "${BLUE}🔍 Dry-run indexation...${NC}"
    $PYTHON -c "
from src.core.indexer import load_paths
paths = load_paths()
for p in paths:
    print(f'📂 {p}')
"
}

help() {
    cat << EOF
☯️  AI Tao - Usage

Commands:
  start              Start all services (API + UI + Sync)
  stop               Stop all services
  restart            Restart all services
  status             Check service health
  check config       Validate config.toml
  check scan         Show what would be indexed (dry-run)
  help               Show this help

Examples:
  ./aitao.sh start
  ./aitao.sh check config
  ./aitao.sh status
EOF
}
```

**Tâches:**
- ✅ Créer AITAO-004 dans le backlog
- Implémenter commandes manquantes
- Ajouter tests shell (bats framework ?)

---

### 8. Fichiers Legacy Inutiles (🧹 Nettoyage)

**État actuel:**
- `data/schema.sql` existe dans le projet
- Contient tables pour **Chainlit** (ancien framework de chat)
- Tables: `users`, `threads`, `steps`, `elements`, `feedbacks`

**Intention PRD:**
> AnythingLLM Integration - AnythingLLM uses its own SQLite DB

**Impact:**
- ❌ **Aucun import de `schema.sql`** dans le code actuel d'AItao
- AnythingLLM utilise `anythingllm-storage/anythingllm.db` (sa propre base)
- Confusion pour nouveaux développeurs : "C'est quoi ce fichier ?"
- Trace du projet legacy (avant migration vers AnythingLLM)

**Preuves:**
```bash
# Recherche dans le code actuel:
grep -r "schema.sql" src/  # ❌ Aucun résultat

# Trouvé seulement dans:
_sources/tmp/aitao_legacy_20260122/run_chat_custom.py  # Archive legacy
```

**Recommandation:**
❌ **SUPPRIMER** `data/schema.sql`

```bash
rm data/schema.sql
git rm data/schema.sql
```

**Tâches:**
- ✅ Créer AITAO-019 dans le backlog (nettoyage)
- ✅ Mettre à jour DEBT-001 pour pointer vers schema.sql
- Vérifier autres fichiers legacy (backups, .bak, etc.)
- Documenter dans CHANGELOG : "Removed Chainlit legacy files"

---

## 📋 Résumé des Actions Prioritaires

### 🔥 Critique (Bloquer V1)
1. **AITAO-001:** Fix Logger to Use PathManager
2. **BUG-001:** Logs Not Created in Configured Directory

### 🚀 Haute Priorité (V1 Must-Have)
3. **AITAO-002:** Centralize PathManager Usage (architecture déjà saine, juste standardiser imports)
4. **AITAO-003:** Add SHA-256 Hash to Metadata
5. **AITAO-004:** Complete CLI Commands
6. **AITAO-005:** Expand File Types (Presentations)
7. **AITAO-007:** Integrate Web Search into UI

### 📦 Moyenne Priorité (V1 Nice-to-Have)
8. **AITAO-006:** Complete Sync Agent
9. **AITAO-010:** Integrate Vision Model
10. **AITAO-011:** Integrate Code Model

### 🧹 Nettoyage (Non-bloquant)
11. **AITAO-019:** Remove Legacy Files (schema.sql)

---

## 🎯 Suggestions Architecturales

### 1. Singleton pour PathManager
**Problème:** Plusieurs instances de PathManager créées = re-parsing config
**Solution:**
```python
# src/core/aitao_configpath.py

_instance = None

def get_path_manager():
    global _instance
    if _instance is None:
        _instance = AitaoPathManager()
    return _instance

# Exportation simplifiée
path_manager = get_path_manager()
```

### 2. Configuration Schema Validation
**Problème:** Erreurs de config découvertes au runtime
**Solution:** Utiliser `pydantic` ou `cerberus` pour valider config.toml au démarrage

```python
from pydantic import BaseModel, validator

class SystemConfig(BaseModel):
    storage_root: str
    logs_path: str
    
    @validator('storage_root')
    def storage_must_be_absolute(cls, v):
        if not os.path.isabs(v):
            raise ValueError('storage_root must be absolute path')
        return v

class AitaoConfig(BaseModel):
    system: SystemConfig
    models: dict
    indexing: dict
```

### 3. Event Bus pour Watch Folders
**Problème:** Besoin de réactivité (auto-indexing)
**Solution:** Implémenter pub/sub interne

```python
# src/core/events.py
from typing import Callable

class EventBus:
    def __init__(self):
        self._listeners = {}
    
    def on(self, event: str, callback: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def emit(self, event: str, data):
        for callback in self._listeners.get(event, []):
            callback(data)

event_bus = EventBus()

# Usage:
# event_bus.on('file.created', lambda data: rag.index_file(data['path']))
```

### 4. Health Check Endpoint
**Problème:** `status` command basique
**Solution:** Endpoint `/health` avec métriques

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "inference": "running",
            "rag": "running",
            "disk_usage": path_manager.get_storage_usage()
        },
        "metrics": {
            "indexed_files": rag.count(),
            "uptime_seconds": get_uptime()
        }
    }
```

---

## ❓ Questions à l'Utilisateur

### 1. Modèles
**Question:** Préférez-vous :
- A) Symlink `_sources/AI-models` → `aitao/models` ?
- B) Copier modèles dans le projet ?
- C) Garder séparé (documenter dans config) ?

**Impact:** Détermine la structure de déploiement

### 2. Licence Open Source
**Question:** Pour commercialiser tout en restant open-source, envisagez-vous :
- MIT License (très permissive, permet usage commercial sans contrainte)
- Apache 2.0 (permissive + protection brevets)
- AGPL (copyleft fort, force partage des modifications)
- Dual License (GPL + licence commerciale payante)

**Recommandation:** Apache 2.0 pour l'équilibre commercialisation/communauté

### 3. Sandboxing
**Question:** Pour la sécurité (PDFs malicieux, scripts dangereux), voulez-vous :
- A) Docker container isolé pour traitement de fichiers
- B) Limitations Python (pas d'exec, imports restreints)
- C) Scanner antivirus avant indexation
- D) Aucune restriction (confiance utilisateur)

**Recommandation:** A + B pour production

---

## 📊 État d'Avancement Global

| Phase | % Complété | Bloquants |
|-------|-----------|-----------|
| Phase 1: Foundation | 65% | AITAO-001, AITAO-002 |
| Phase 2: Core Features | 25% | Phase 1 completion |
| Phase 3: Advanced | 5% | Phase 2 completion |
| Phase 4: Polish | 0% | Phase 3 completion |

**Estimation V1 Launch:** 6-8 semaines (si focus sur stories critiques)

---

*Document vivant - Mettre à jour après chaque sprint*
