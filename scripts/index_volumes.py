#!/usr/bin/env python3
"""
Index Volumes - Simple indexing utility

Deprecated: Use benchmark_indexing.py for performance testing
This script remains for quick ad-hoc indexing tests.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.core.kotaemon_indexer import AITaoIndexer
from src.core.path_manager import path_manager
from src.core.logger import get_logger

logger = get_logger("IndexVolumes", "index_volumes.log")


def main():
    """Index _Volumes folder and display stats."""
    logger.info("=" * 70)
    logger.info("🚀 AI TAO - INDEXATION _VOLUMES (246 FICHIERS)")
    logger.info("=" * 70)
    
    # Get _Volumes path from config
    config = path_manager.get_indexing_config()
    paths = config.get("include_paths", [])
    
    if not paths:
        logger.error("❌ Aucun chemin configuré dans config.toml > indexing.include_paths")
        return 1
    
    volumes_path = paths[0]  # /Users/phil/Downloads/_Volumes/
    logger.info(f"📂 Dossier à indexer: {volumes_path}")
    
    if not os.path.exists(volumes_path):
        logger.error(f"❌ Dossier inexistant: {volumes_path}")
        return 1
    
    # Initialize indexer
    logger.info("\n🔧 Initialisation de l'indexeur...")
    indexer = AITaoIndexer(collection_name="default")
    
    if not indexer.is_enabled():
        logger.error("❌ Indexeur non disponible. Vérifiez les dépendances.")
        return 1
    
    logger.info("✅ Indexeur prêt (LanceDB + sentence-transformers)")
    
    # Count files before indexing
    logger.info("\n📊 Analyse du dossier...")
    file_count = 0
    for root, _, files in os.walk(volumes_path):
        for f in files:
            if not f.startswith('.'):
                file_count += 1
    
    logger.info(f"📄 {file_count} fichier(s) trouvé(s)")
    
    # Start indexing
    logger.info("\n⏳ Indexation en cours...")
    logger.info("   (Les PDFs et fichiers volumineux peuvent prendre du temps)")
    
    start_time = time.time()
    
    # Index with supported extensions only
    indexed_count = indexer.index_folder(
        volumes_path,
        recursive=True,
        exts={".txt", ".md", ".pdf", ".json", ".html"}  # Start with text-based formats
    )
    
    elapsed = time.time() - start_time
    
    # Display results
    logger.info("\n" + "=" * 70)
    logger.info("📊 RÉSULTATS")
    logger.info("=" * 70)
    logger.info(f"✅ Fichiers indexés: {indexed_count}/{file_count}")
    logger.info(f"⏱️  Temps d'exécution: {elapsed:.2f}s")
    
    if indexed_count > 0:
        logger.info(f"📈 Vitesse moyenne: {indexed_count/elapsed:.1f} fichiers/seconde")
    
    # Get stats
    stats = indexer.get_stats()
    logger.info(f"\n📦 Stats LanceDB:")
    logger.info(f"   • Documents: {stats.get('document_count', 0)}")
    logger.info(f"   • Collection: {stats.get('collection', 'N/A')}")
    
    # Test search
    logger.info("\n" + "=" * 70)
    logger.info("🔍 TEST DE RECHERCHE")
    logger.info("=" * 70)
    
    test_queries = [
        "règlement intérieur",
        "tarifs",
        "川普關稅",  # Trump tariffs in Chinese
    ]
    
    for query in test_queries:
        logger.info(f"\n🔎 Requête: '{query}'")
        results = indexer.search(query, limit=3)
        logger.info(f"   Résultats: {len(results)}")
        
        for i, result in enumerate(results[:3], 1):
            filename = result.get("filename", "N/A")
            logger.info(f"   {i}. {filename}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ INDEXATION TERMINÉE")
    logger.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
