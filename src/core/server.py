#!/usr/bin/env python3
"""
Serveur API compatible OpenAI - Core Moteur AI Tao
Expose les modèles GGUF locaux via une API standard.
"""

import os
import sys
import argparse
import toml
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from llama_cpp.server.app import create_app
from llama_cpp.server.settings import ServerSettings, ModelSettings

# ... imports ...
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from llama_cpp.server.app import create_app
from llama_cpp.server.settings import ServerSettings, ModelSettings

# Import indexer logic and path manager
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from core.indexer import index_directory_generator, load_config, load_paths
from core.path_manager import path_manager

# --- Job Management ---
class JobStatus:
    def __init__(self):
        self.state = "idle" # idle, running, completed, error
        self.progress = 0.0
        self.message = ""
        self.logs = []
        # New stats for details
        self.current_vol = ""
        self.vol_processed = 0
        self.vol_total = 0

job_manager = JobStatus()

def run_background_indexing():
    """Task that runs in background controlled by FastAPI"""
    job_manager.state = "running"
    job_manager.progress = 0.0
    job_manager.logs = []
    
    try:
        # Reload config to ensure we have the latest user changes
        path_manager.load_config()
        
        paths = load_paths()
        if not paths:
            job_manager.message = "No sources configured."
            job_manager.state = "completed"
            return

        total_sources = len(paths)
        
        for idx, src_path in enumerate(paths):
            vol_name = os.path.basename(src_path)
            job_manager.message = f"Indexing {vol_name}..."
            job_manager.current_vol = vol_name
            job_manager.vol_processed = 0
            job_manager.vol_total = 0
            
            for type_, data in index_directory_generator(src_path):
                if type_ == "progress":
                     # New format: (current, total)
                     curr, total = data
                     job_manager.vol_processed = curr
                     job_manager.vol_total = total
                     
                     # Global progress: (current_source_idx + local_pct) / total_sources
                     local_pct = (curr / total) if total > 0 else 0
                     global_prog = (idx + local_pct) / total_sources
                     job_manager.progress = min(global_prog, 1.0)
                     
                elif type_ == "result":
                     job_manager.logs.append(f"Completed: {vol_name}")
                elif type_ == "error" or type_ == "log":
                     # Keep only last 5 logs to save memory
                     if len(job_manager.logs) > 5: job_manager.logs.pop(0)
                     job_manager.logs.append(str(data))
                     
            # End of source
            job_manager.progress = (idx + 1) / total_sources

        job_manager.state = "completed"
        job_manager.message = "All sources indexed."
        
    except Exception as e:
        job_manager.state = "error"
        job_manager.message = str(e)

# --- FastAPI Extensions ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    yield
    # Shutdown logic


def get_model_path(model_name="llama3-8b"):
    """Récupère le chemin absolu avec un fallback intelligent via PathManager."""
    models_dir = path_manager.get_models_dir()
    
    # Mapping relatif au models_dir
    # Note: MODELS_MAP utilisé par chat_app.py pour lister les modèles dispos
    rel_map = MODELS_MAP

    # Helper to check existence
    def verify(rel_path):
        p = models_dir / rel_path
        return str(p) if p.exists() else None

    # 1. Check requested model
    target_rel = rel_map.get(model_name)
    if target_rel:
        found = verify(target_rel)
        if found: return found

    # 2. Search fallback in map
    print(f"⚠️ Modèle '{model_name}' introuvable ou n'existe pas. Recherche fallback...")
    for name, rel in rel_map.items():
        found = verify(rel)
        if found:
            print(f"🔄 Fallback sur : {name}")
            return found
            
    # 3. Last resort: scan dir for any .gguf
    print("⚠️ Aucun modèle mappé trouvé. Scan du dossier...")
    for f in models_dir.glob("**/*.gguf"):
        return str(f)
        
    return None

# Definition globale des modèles disponibles (Relatifs)
MODELS_MAP = {
    "llama3-8b": "llama3.1-8b/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    "qwen2-coder": "Qwen-2.5-Coder/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
    "qwen2-vl": "qwen2-vl-7b/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Tao API Server")
    parser.add_argument("--model", type=str, default="llama3-8b", help="Modèle à charger au démarrage")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Hôte")
    parser.add_argument("--port", type=int, default=8000, help="Port API")
    parser.add_argument("--n_ctx", type=int, default=8192, help="Contexte tokens")
    
    args = parser.parse_args()

    model_path = get_model_path(args.model)
    if not model_path:
        print("❌ Aucun modèle .gguf trouvé. Lancez le téléchargement d'abord.")
        sys.exit(1)

    print(f"\n🚀 AI Tao Engine Starting...")
    print(f"📂 Model: {os.path.basename(model_path)}")
    print(f"🔗 API: http://{args.host}:{args.port}")
    print(f"📖 Docs: http://{args.host}:{args.port}/docs\n")

    # Configuration du serveur Llama
    server_settings = ServerSettings(host=args.host, port=args.port)
    model_settings = ModelSettings(
        model=model_path,
        n_ctx=args.n_ctx,
        n_gpu_layers=-1, # Tout sur le GPU M1
        verbose=False
    )

    # Création et lancement app FastAPI
    app = create_app(server_settings=server_settings, model_settings=[model_settings])

    # --- Router pour le RAG System ---
    @app.post("/v1/system/scan")
    async def trigger_scan(background_tasks: BackgroundTasks):
        if job_manager.state == "running":
            return {"status": "busy", "message": "Indexation déjà en cours"}
        
        background_tasks.add_task(run_background_indexing)
        return {"status": "started", "message": "Indexation lancée en arrière-plan"}

    @app.get("/v1/system/status")
    async def get_status():
        return {
            "state": job_manager.state,
            "progress": job_manager.progress,
            "message": job_manager.message,
            "logs": job_manager.logs,
            # Stats
            "current_vol": getattr(job_manager, 'current_vol', ""),
            "vol_processed": getattr(job_manager, 'vol_processed', 0),
            "vol_total": getattr(job_manager, 'vol_total', 0)
        }
    
    import uvicorn
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info"
    )
