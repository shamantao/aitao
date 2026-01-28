import os
import glob
from typing import List
try:
    from src.core.rag import rag, RagEngine
except ImportError:
    from core.rag import rag, RagEngine

try:
    from src.core.path_manager import path_manager
except ImportError:
    from core.path_manager import path_manager

def load_config():
    """Récupère la configuration d'indexation via PathManager."""
    return path_manager.get_indexing_config()

def load_paths():
    """Récupère la liste des chemins sources via PathManager."""
    return load_config().get("include_paths", [])


def index_directory_generator(path: str, user_config=None):
    """Générateur pour l'indexation (permet d'afficher la progression)."""
    
    # Load config if not provided
    conf = user_config if user_config else load_config()
    
    # Adaptation au format retourné par path_manager vs ancien format
    ignore_dirs = set(d.lower() for d in conf.get("exclude_dirs", []))
    ignore_files = set(f.lower() for f in conf.get("exclude_files", []))
    ignore_exts = set(e.lower() for e in conf.get("exclude_extensions", []))
    
    # Compatibilité avec ancien nommage si user_config manuel passé
    ignore_dirs.update(set(d.lower() for d in conf.get("ignore_dirs", []))) 

    SUPPORTED_EXTENSIONS = {'.md', '.txt', '.py', '.sh', '.json', '.html', '.js', '.ts', '.css', '.mdx', '.rst'}

    if not os.path.exists(path):
        yield "error", f"Le chemin '{path}' n'existe pas."
        return

    files_found = []
    # Scan des fichiers
    yield "status", "🔍 Scan des fichiers en cours..."
    for root, dirs, files in os.walk(path):
        # Filtrer les dossiers ignorés
        dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs]
        
        for file in files:
            # Filtrer les fichiers ignorés par nom complet
            if file.lower() in ignore_files:
                continue
                
            ext = os.path.splitext(file)[1].lower()
            
            # Filtrer par extension exclue
            if ext in ignore_exts:
                continue
                
            if ext in SUPPORTED_EXTENSIONS:
                files_found.append(os.path.join(root, file))
    
    total_files = len(files_found)
    yield "status", f"📄 {total_files} fichiers éligibles trouvés."
    
    # Traitement
    indexed_count = 0
    errors_count = 0
    
    for i, file_path in enumerate(files_found):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if not content.strip():
                continue

            # 1. Nettoyage préventif (Deduplication)
            # On supprime les anciennes entrées de ce fichier avant d'ajouter les nouvelles
            rel_path = os.path.relpath(file_path, path)
            rag.delete_by_source(rel_path)

            # Chunking basique (Découpage en blocs de 1000 chars pour l'instant)
            # Amélioration possible: Chunking sémantique
            chunk_size = 1000
            chunks = [content[j:j+chunk_size] for j in range(0, len(content), chunk_size)]
            
            # Préparation du batch
            batch_items = []
            
            for chunk in chunks:
                if len(chunk) > 50: # Ignorer les trop petits bouts
                    batch_items.append({
                        "text": chunk,
                        "metadata": {
                            "source": rel_path,
                            "filename": os.path.basename(file_path),
                            "type": "code" if file_path.endswith(('.py', '.js', '.sh')) else "doc"
                        }
                    })
            
            # Ajout groupé (Plus rapide et atomique)
            if batch_items:
                rag.add_documents_batch(batch_items)
            
            indexed_count += 1
            # Yield progression every 5 files or last one
            if i % 5 == 0 or i == total_files - 1:
                # Renvoie (index_courant, total_fichiers)
                yield "progress", (i + 1, total_files)
                
        except Exception as e:
            errors_count += 1
            yield "log", f"Erreur sur {os.path.basename(file_path)}: {e}"

    yield "result", f"Terminé ! {indexed_count} fichiers indexés, {errors_count} erreurs."
