#!/usr/bin/env python3
"""
Reset AI Tao - Clean all indexes, databases, conversations and caches

Responsibilities:
- Remove LanceDB vector store
- Remove failed files tracking
- Clear conversation history
- Reset logs (optional)
- Prepare for fresh indexing run
"""

import os
import sys
import shutil
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.core.path_manager import path_manager
from src.core.logger import get_logger

logger = get_logger("ResetAITao", "reset_aitao.log")


def reset_aitao(keep_logs: bool = True) -> None:
    """Clean all AI Tao data stores.
    
    Args:
        keep_logs: If True, preserve log files
    """
    logger.info("=" * 70)
    logger.info("🧹 AI TAO - RESET COMPLET")
    logger.info("=" * 70)
    
    storage_root = path_manager.get_storage_root()
    
    # 1. LanceDB vector store
    vector_db = storage_root / "lancedb"
    if vector_db.exists():
        logger.info(f"🗑️  Suppression LanceDB: {vector_db}")
        shutil.rmtree(vector_db)
        logger.info("✅ LanceDB supprimé")
    
    # 2. Failed files tracker
    failed_files = storage_root / "failed_files.json"
    if failed_files.exists():
        logger.info(f"🗑️  Suppression failed files: {failed_files}")
        failed_files.unlink()
        logger.info("✅ Failed files supprimé")
    
    # 3. Conversation history
    history_db = storage_root / "history" / "chat_history.db"
    if history_db.exists():
        logger.info(f"🗑️  Suppression historique conversations: {history_db}")
        history_db.unlink()
        logger.info("✅ Historique supprimé")
    
    # 4. Logs (optional)
    if not keep_logs:
        logs_dir = path_manager.get_logs_dir()
        if logs_dir.exists():
            logger.info(f"🗑️  Suppression logs: {logs_dir}")
            shutil.rmtree(logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)
            logger.info("✅ Logs supprimés")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ RESET TERMINÉ - Système prêt pour indexation vierge")
    logger.info("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset AI Tao data stores")
    parser.add_argument(
        "--clear-logs",
        action="store_true",
        help="Also clear log files (default: keep logs)"
    )
    
    args = parser.parse_args()
    reset_aitao(keep_logs=not args.clear_logs)
