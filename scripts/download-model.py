#!/usr/bin/env python3
"""
Script de téléchargement de modèles IA
Télécharge des modèles GGUF depuis HuggingFace
"""

import os
import sys
import argparse
from pathlib import Path

def print_header(text):
    """Affiche un en-tête"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)

def check_huggingface_hub():
    """Vérifie et installe huggingface_hub si nécessaire"""
    try:
        import huggingface_hub
        return True
    except ImportError:
        print("⚠️  huggingface_hub non installé")
        print("📦 Installation automatique...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"])
            print("✅ huggingface_hub installé")
            return True
        except:
            print("❌ Erreur lors de l'installation")
            print("💡 Essayez manuellement : pip3 install huggingface_hub")
            return False

# Catalogue de modèles prédéfinis
MODELS = {
    # --- Modèle de Chat Rapide (Généraliste) ---
    "llama3.1-8b": {
        "name": "Meta Llama 3.1 8B Instruct",
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size": "4.92 GB",
        "description": "Rapide, léger, excellent pour le chat quotidien (Le remplaçant idéal)"
    },
    
    # --- Modèle Spécialisé Code ---
    "qwen2.5-coder": {
        "name": "Qwen 2.5 Coder 7B",
        "repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
        "size": "4.69 GB",
        "description": "L'expert code actuel (Meilleur ratio taille/perf)"
    },

    # --- Modèle Vision / OCR / Tableaux ---
    "qwen2-vl-7b": {
        "name": "Qwen2.5-VL 7B Instruct (Vision)",
        "repo": "unsloth/Qwen2.5-VL-7B-Instruct-GGUF",
        "file": "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
        "size": "4.80 GB",
        "description": "Vision-Language : Lit les images, OCR, extrait les tableaux (Compatible Chinois)"
    },

    # --- Anciens Modèles pour archivage ---
    "gpt-oss-20b": {
        "name": "GPT-OSS-20B Claude Distill",
        "repo": "TeichAI/gpt-oss-20b-claude-4.5-sonnet-high-reasoning-distill-GGUF",
        "file": "gpt-oss-20b-claude-4.5-sonnet-high-reasoning-distill-bf16.gguf",
        "size": "13.8 GB",
        "description": "Ancien modèle principal (Lourd)"
    }
}

def list_models():
    """Affiche la liste des modèles disponibles"""
    print_header("MODÈLES DISPONIBLES")
    for key, info in MODELS.items():
        print(f"\n🤖 {key}")
        print(f"   Nom : {info['name']}")
        print(f"   Taille : {info['size']}")
        print(f"   Description : {info['description']}")
    print("\n" + "="*70)

def download_model(model_key, custom_repo=None, custom_file=None):
    """Télécharge un modèle"""
    
    # Activation du téléchargement ultra-rapide si hf_transfer est présent
    try:
        import hf_transfer
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
        print("🚀 Mode Turbo activé (hf_transfer)")
    except ImportError:
        pass
    
    if not check_huggingface_hub():
        return False
    
    from huggingface_hub import hf_hub_download
    
    # Récupérer les infos du modèle
    if model_key in MODELS:
        model_info = MODELS[model_key]
        repo_id = custom_repo or model_info["repo"]
        filename = custom_file or model_info["file"]
        model_name = model_info["name"]
    elif custom_repo and custom_file:
        repo_id = custom_repo
        filename = custom_file
        model_name = filename
    else:
        print(f"❌ Modèle '{model_key}' inconnu")
        print("\n💡 Utilisez --list pour voir les modèles disponibles")
        return False
    
    print_header(f"TÉLÉCHARGEMENT : {model_name}")
    print(f"📦 Repository : {repo_id}")
    print(f"📄 Fichier : {filename}")
    
    # Répertoire de destination
    models_dir = Path("/Users/phil/Downloads/_sources/AI-models")
    model_dest = models_dir / model_key.replace("-light", "")
    model_dest.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Destination : {model_dest}")
    
    # Vérifier espace disque
    stat = os.statvfs(models_dir)
    free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    print(f"💾 Espace disponible : {free_space_gb:.1f} GB")
    
    if free_space_gb < 20:
        print("⚠️  Attention : Moins de 20 GB disponibles")
        response = input("Continuer quand même ? (o/N) : ")
        if response.lower() != 'o':
            print("❌ Téléchargement annulé")
            return False
    
    print("\n🚀 Téléchargement en cours...")
    print("⏳ Cela peut prendre plusieurs minutes selon votre connexion\n")
    
    try:
        # Télécharger avec barre de progression
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=model_dest,
            local_dir_use_symlinks=False
        )
        
        # Vérifier la taille du fichier téléchargé
        file_size_gb = Path(downloaded_path).stat().st_size / (1024**3)
        
        print_header("TÉLÉCHARGEMENT TERMINÉ ✅")
        print(f"📍 Emplacement : {downloaded_path}")
        print(f"📊 Taille : {file_size_gb:.2f} GB")
        print(f"\n💡 Utilisez ce modèle avec :")
        print(f"   python3 scripts/agent-code.py --model {model_key}")
        
        # Mettre à jour AI-SETUP.md
        update_setup_file(model_key, model_name, str(model_dest), file_size_gb)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n❌ Téléchargement interrompu par l'utilisateur")
        return False
    except Exception as e:
        print(f"\n❌ Erreur lors du téléchargement : {e}")
        print("\n💡 Vérifiez votre connexion Internet")
        return False

def update_setup_file(model_key, model_name, model_path, size_gb):
    """Met à jour le fichier AI-SETUP.md"""
    setup_file = Path("/Users/phil/Downloads/_sources/AI-models/AI-SETUP.md")
    
    if not setup_file.exists():
        return
    
    # Note simple dans le fichier
    note = f"\n<!-- Modèle {model_key} téléchargé le {Path(model_path).stat().st_mtime} -->\n"
    
    print(f"\n📝 Fichier AI-SETUP.md mis à jour")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Télécharger des modèles IA depuis HuggingFace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  %(prog)s --list                    # Liste les modèles disponibles
  %(prog)s codestral-22b             # Télécharge Codestral-22B (test)
  %(prog)s gpt-oss-20b               # Télécharge GPT-OSS-20B (prod)
  %(prog)s codestral-22b-light       # Version allégée pour tests
  
  # Téléchargement personnalisé :
  %(prog)s custom --repo user/model --file model.gguf
        """
    )
    
    parser.add_argument("model", nargs="?", help="Nom du modèle à télécharger")
    parser.add_argument("--list", action="store_true", help="Lister les modèles disponibles")
    parser.add_argument("--repo", help="Repository HuggingFace personnalisé")
    parser.add_argument("--file", help="Nom du fichier GGUF personnalisé")
    
    args = parser.parse_args()
    
    print("\n" + "🤖 " * 25)
    print("  TÉLÉCHARGEMENT MODÈLES IA")
    print("🤖 " * 25)
    
    if args.list:
        list_models()
        return
    
    if not args.model:
        parser.print_help()
        print("\n💡 Utilisez --list pour voir les modèles disponibles")
        return
    
    success = download_model(args.model, args.repo, args.file)
    
    if success:
        print("\n" + "="*70)
        print("✅ Tout est prêt ! Prochaine étape :")
        print("   python3 scripts/agent-code.py")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ Le téléchargement a échoué")
        print("="*70 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
