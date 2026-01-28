# Plan de nettoyage AItao V2

## ✅ À GARDER (à améliorer si besoin)

### src/core/
- **lib/path_manager.py** ✅ Base générique solide
- **aitao_configpath.py** ✅ PathManager spécifique Aitao (à renommer → `pathmanager.py`)
- **logger.py** ✅ Logger fonctionnel (à améliorer format JSON)
- **path_manager.py** ⚠️ SHIM FILE → à supprimer après refacto imports

### config/
- **config.toml** ✅ Garder structure, adapter à V2

### scripts/
- **bench_qwen_vl_mmproj.py** ✅ Référence benchmarks
- **check_system.py** ✅ Utilitaire validation

---

## ❌ À SUPPRIMER (dette technique V1 / hors scope V2)

### src/core/ - Services V1 à supprimer
- **admin_dashboard.py** ❌ UI AnythingLLM (hors scope)
- **server.py** ❌ Serveur V1 (remplacé par FastAPI)
- **web.py** ❌ Web search (hors scope MVP V2)
- **rag_server.py** ❌ RAG V1 (à reconstruire proprement)
- **kotaemon_indexer.py** ❌ Kotaemon (pas utilisé)
- **anythingllm_client.py** ❌ AnythingLLM (hors scope V2)
- **sync_agent.py** ❌ Sync AnythingLLM (hors scope V2)
- **rag.py** ❌ RAG V1 (à reconstruire)
- **indexer.py** ❌ Indexer V1 (à reconstruire modulaire)
- **failed_files_tracker.py** ⚠️ À revoir (peut servir mais à simplifier)
- **warnings_config.py** ❌ Utilitaire secondaire

---

## 🔄 Actions à faire

### 1. Restructurer src/core/ (Foundation)
```
src/core/
├── __init__.py
├── pathmanager.py       ← Renommer aitao_configpath.py
├── logger.py            ← Améliorer (JSON structuré)
├── config.py            ← NOUVEAU : ConfigManager YAML
├── system_monitor.py    ← NOUVEAU : CPU/RAM monitoring
└── lib/
    └── path_manager.py  ← Garder base générique
```

### 2. Créer nouvelles structures V2
```
src/
├── core/          ← Foundation (ci-dessus)
├── indexation/    ← NOUVEAU : Scanner, Queue, Worker, TextExtractor
├── search/        ← NOUVEAU : LanceDB, Meilisearch, Hybrid
├── ocr/           ← NOUVEAU : Router, AppleScript, Qwen-VL
├── translation/   ← NOUVEAU : Translator, ActionExtractor
├── api/           ← NOUVEAU : FastAPI routes
└── dashboard/     ← NOUVEAU : TUI (Rich)
```

### 3. Supprimer fichiers obsolètes
```bash
# Services V1 AnythingLLM
rm src/core/admin_dashboard.py
rm src/core/anythingllm_client.py
rm src/core/sync_agent.py
rm src/core/kotaemon_indexer.py

# Services V1 à reconstruire
rm src/core/server.py
rm src/core/rag_server.py
rm src/core/rag.py
rm src/core/indexer.py

# Hors scope
rm src/core/web.py
rm src/core/warnings_config.py

# À revoir plus tard
# rm src/core/failed_files_tracker.py  # Peut servir, à simplifier
```

### 4. Nettoyer scripts/
- Garder benchmarks (référence)
- Supprimer scripts obsolètes AnythingLLM

---

## ✅ Validation avant nettoyage

**Checklist :**
- [ ] PathManager V1 fonctionne → OK
- [ ] Logger V1 fonctionne → OK
- [ ] Config.toml existe → OK
- [ ] Aucune dépendance critique sur fichiers à supprimer → À vérifier

**Confirmation utilisateur requise avant suppression massive.**
