#!/usr/bin/env python3
"""
Script de gestion de l'indexation AI Tao.
Source de vérité : config/config.toml (section via PathManager)
"""
import sys
import os
import argparse
import requests
import time
import shutil

# Add project root to path to ensure imports work
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.core.aitao_configpath import path_manager
    # We need a writer. PathManager uses tomllib (read-only).
    # We use 'toml' lib if installed, or we fail if write is needed.
    import toml 
except ImportError as e:
    # If toml is not installed but we only want to scan, we might survive?
    # But this script is for adding paths usually.
    toml = None

API_URL = "http://localhost:18000"

def add_path_to_config_file(new_path):
    """
    Édite le fichier config.toml pour ajouter un chemin.
    Note: PathManager est Read-Only par nature sur la structure chargée,
    nous devons donc éditer le fichier physiquement.
    """
    if toml is None:
        print("❌ Erreur: La librairie 'toml' est requise pour modifier la configuration.")
        print("pip install toml")
        sys.exit(1)

    config_file = path_manager.config_path
    abs_path = os.path.abspath(new_path)
    
    if not os.path.exists(abs_path):
        print(f"❌ Erreur: Le chemin {abs_path} n'existe pas.")
        sys.exit(1)

    print(f"📝 Modification de {config_file}...")
    
    try:
        # Lecture
        with open(config_file, "r") as f:
            data = toml.load(f)
        
        # Structure par défaut si absente
        if "indexing" not in data:
            data["indexing"] = {}
        if "include_paths" not in data["indexing"]:
            data["indexing"]["include_paths"] = []
            
        current_paths = data["indexing"]["include_paths"]
        
        # Validation format (ensure strings)
        current_paths = [str(p) for p in current_paths] 

        # Check doublons (simple string check)
        if abs_path in current_paths:
            print(f"📂 Déjà configuré : {abs_path}")
            return False
            
        # Ajout
        current_paths.append(abs_path)
        data["indexing"]["include_paths"] = current_paths
        
        # Écriture
        with open(config_file, "w") as f:
            toml.dump(data, f)
            
        print(f"✅ Configuration mise à jour : ajouté {abs_path}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'édition du config: {e}")
        return False

def trigger_remote_scan():
    print("🚀 Demande de scan à l'API...")
    try:
        # 1. Trigger
        res = requests.post(f"{API_URL}/v1/system/scan")
        if res.status_code != 200:
            if "busy" in res.text:
                print("⚠️  Le moteur est déjà occupé. Connexion au flux existant...")
            else:
                print(f"❌ Erreur API ({res.status_code}): {res.text}")
                return
        else:
             print("✅ Scan démarré.")
        
        # 2. Monitor
        print("⏳ Suivi de l'avancement...")
        
        last_vol = ""
        last_processed = 0
        last_time = time.time()

        while True:
            try:
                r = requests.get(f"{API_URL}/v1/system/status")
                if r.status_code != 200:
                    time.sleep(1)
                    continue

                status = r.json()
                state = status.get("state")
                progress = status.get("progress", 0)
                msg = status.get("message", "")
                
                # Stats (nouvelle API)
                curr_vol = status.get("current_vol", "")
                curr_processed = status.get("vol_processed", 0)
                curr_total = status.get("vol_total", 0)
                
                # Calul vitesse (files/sec)
                now = time.time()
                dt = now - last_time
                speed = 0.0
                
                if curr_vol == last_vol and dt > 0:
                     d_processed = curr_processed - last_processed
                     # Moyenne simple
                     speed = d_processed / dt if d_processed >= 0 else 0
                
                # Mise à jour références
                last_vol = curr_vol
                last_processed = curr_processed
                last_time = now

                # Rendu barre
                try:
                    cols, _ = shutil.get_terminal_size((80, 20))
                except Exception:
                    cols = 80

                bar_len = 20
                filled = int(bar_len * progress)
                bar = "█" * filled + "░" * (bar_len - filled)
                
                # Construction Info: Vol: _Volumes | 350/1000 | 12.0 f/s
                if curr_vol:
                    info_str = f"Vol: {curr_vol} | {curr_processed}/{curr_total} | {speed:.1f} f/s"
                else:
                    info_str = msg.strip()

                # Calculate available space
                prefix = f"[{bar}] {int(progress * 100)}% | "
                avail = max(10, cols - len(prefix) - 2)
                
                if len(info_str) > avail:
                    info_str = info_str[:avail-3] + "..."

                # \033[K clear line after cursor
                print(f"\r{prefix}{info_str:<{avail}}", end="")
                sys.stdout.flush()
                
                if state == "completed":
                    print("\n🎉 Indexation terminée !")
                    break
                if state == "error":
                    print(f"\n❌ Erreur indexation: {msg}")
                    break
                    
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Suivi interrompu (le background job continue).")
                break
            except Exception as e:
                 print(f"\n❌ Erreur connexion status: {e}")
                 break
                
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Impossible de contacter l'API sur {API_URL}")
        print("💡 Vérifiez que le serveur est lancé : ./aitao.sh start")

def main():
    parser = argparse.ArgumentParser(description="Outil client pour indexer des fichiers via l'API AI Tao")
    parser.add_argument("path", nargs="?", help="Chemin optionnel à ajouter au config.toml.")
    parser.add_argument("--scan-only", action="store_true", help="Force le scan sans ajouts.")
    args = parser.parse_args()

    should_scan = True
    
    if args.path:
        changed = add_path_to_config_file(args.path)
        # Si ça a changé, on scanne. Si c'est déjà là, on scanne aussi (pour mise à jour).
    
    if should_scan:
        trigger_remote_scan()

if __name__ == "__main__":
    main()
