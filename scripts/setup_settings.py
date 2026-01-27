#!/usr/bin/env python3
"""
Setup System Settings
Configure l'apparence et les messages d'AnythingLLM via des requêtes SQL directes (plus fiable que l'API pour les settings système).
"""
import sqlite3
import sys
import os

# Adapt path manually as we are in scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
except ImportError:
    print("Setup: Impossible d'importer path_manager.")
    sys.exit(1)

logger = get_logger("SetupSystem")

def get_db_path():
    storage = path_manager.get_storage_root()
    return storage / "anythingllm-storage" / "anythingllm.db"

def update_settings():
    db_path = get_db_path()
    if not db_path.exists():
        logger.error(f"DB introuvable à {db_path}")
        return False

    welcome_message = (
        "**AI Tao** est né du besoin simple de préserver l'environnement et d'avoir un assistant personnel "
        "capable de vous aider dans vos tâches quotidiennes sur votre machine, avec un maximum de sécurité. "
        "Et tout cela gratuitement, sans que ce soit vous le produit."
    )

    settings_to_update = {
        # Identité
        "system_instance_name": "AI Tao",
        # "system_logo_filename": "aitao-logo.png", # À faire plus tard
        
        # UI Cleanup (Marque blanche)
        "show_community_link": "false",
        "show_footer_company_logo": "false",
        "show_git_hub_link": "false",
        "show_docs_link": "false",
        
        # Message d'accueil par défaut pour les nouveaux workspaces ? 
        # Note: AnythingLLM a des "System Prompt" mais le message de bienvenue dashboard est souvent hardcodé ou via `welcome_messages` table.
        # Vérifions si on peut injecter un message global.
    }

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Update System Settings
        for key, value in settings_to_update.items():
            cursor.execute(
                "INSERT INTO system_settings (label, value) VALUES (?, ?) ON CONFLICT(label) DO UPDATE SET value=excluded.value;",
                (key, value)
            )
        
        # 2. Update Welcome Message (Table dedicated)
        # AnythingLLM uses `welcome_messages` table for the dashboard random quotes or onboarding.
        # Let's clean it and put ours.
        cursor.execute("DELETE FROM welcome_messages;")
        # Column name is orderIndex, not order
        cursor.execute("INSERT INTO welcome_messages (user, response, orderIndex) VALUES (?, ?, ?);", ("System", welcome_message, 0))

        conn.commit()
        conn.close()
        logger.info("✅ Configuration Système & Message d'accueil mis à jour.")
        return True

    except Exception as e:
        logger.error(f"Erreur Update Settings: {e}")
        return False

if __name__ == "__main__":
    update_settings()
