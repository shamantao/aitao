#!/usr/bin/env python3
"""
Sync Agent - AI Tao
Moniteurs local folders defined in config.toml and triggers indexation (via AITaoIndexer).
"""

import asyncio
import os
import signal
import sys
from watchfiles import awatch, Change

# Add project root to sys.path if needed
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
    from src.core.kotaemon_indexer import AITaoIndexer
except ImportError:
    # Local dev fallback
    from core.path_manager import path_manager
    from core.logger import get_logger
    from core.kotaemon_indexer import AITaoIndexer

logger = get_logger("SyncAgent", "sync_agent.log")

class SyncAgent:
    """Monitor and index files via AITaoIndexer (local LanceDB + sentence-transformers)."""

    def __init__(self):
        self.running = True
        self.config = path_manager.get_indexing_config()
        self.paths = self.config.get("include_paths", [])
        self.indexer = AITaoIndexer(collection_name="default")
        
    async def start(self):
        """Start the file watcher and begin indexation."""
        logger.info("🚀 Sync Agent: Démarrage...")
        
        # 1. Check if indexer is available
        if not self.indexer.is_enabled():
            logger.error("❌ Indexer not available. Verify lancedb and sentence-transformers are installed.")
            return

        logger.info("✅ Indexer ready (LanceDB + sentence-transformers)")

        # 2. Check if we have paths to watch
        if not self.paths:
            logger.warning("⚠️ Aucun dossier à surveiller (config.toml > indexing.include_paths vide)")
            logger.info("💤 Mode veille (aucune surveillance active)...")
            # Keep alive but idle
            while self.running:
                await asyncio.sleep(60)
            return

        # Filter valid paths
        valid_paths = [p for p in self.paths if os.path.exists(p)]
        if not valid_paths:
            logger.error("❌ Aucun chemin valide trouvé dans config.toml")
            logger.info("💤 Mode veille...")
            while self.running:
                await asyncio.sleep(60)
            return

        logger.info(f"👀 Surveillance fichiers active sur: {len(valid_paths)} dossier(s)")
        for vp in valid_paths:
            logger.info(f"   📂 {vp}")
            # Pre-index existing files in folder
            logger.info(f"   📚 Indexation initiale de {vp}...")
            # Index all files in folder (AITaoIndexer uses index_files() for batch processing)
            try:
                from pathlib import Path
                files_to_index = []
                for root, _, filenames in os.walk(vp):
                    for fname in filenames:
                        files_to_index.append(Path(root) / fname)
                count = self.indexer.index_files(files_to_index)
                logger.info(f"   ✅ {count} fichier(s) indexé(s)")
            except Exception as e:
                logger.error(f"   ❌ Erreur indexation {vp}: {e}")
                count = 0

        # 3. Start file watcher (blocking async loop)
        try:
            async for changes in awatch(*valid_paths, stop_event=self._stop_event):
                for change in changes:
                    await self.handle_change(change[0], change[1])
        except Exception as e:
            logger.error(f"❌ Erreur Watcher: {e}")

    async def handle_change(self, change_type, file_path):
        """Callback executed when a file changes.
        
        Args:
            change_type: watchfiles.Change enum (added=1, modified=2, deleted=3)
            file_path: Path to the changed file
        """
        # Change type mapping
        c_map = {Change.added: "AJOUTÉ", Change.modified: "MODIFIÉ", Change.deleted: "SUPPRIMÉ"}
        c_str = c_map.get(change_type, "INCONNU")

        logger.info(f"⚡️ {c_str}: {file_path}")

        # Only index on add or modify
        if change_type in [Change.added, Change.modified]:
            logger.info(f"📤 Indexation en cours pour {file_path}...")
            count = self.indexer.index_files([file_path])
            if count > 0:
                logger.info(f"✨ Fichier indexé avec succès")
            else:
                logger.warning(f"⚠️ Fichier non indexé (format non supporté ou lecture échouée)")
        elif change_type == Change.deleted:
            # Deletion would require a delete method in AITaoIndexer
            # For now, we skip deletion handling
            logger.debug(f"Suppression detected (pas de suppression auto pour l'instant)")

    @property
    def _stop_event(self):
        """Create a stop event for watchfiles."""
        event = asyncio.Event()
        if not self.running:
            event.set()
        return event

    def stop(self):
        """Stop the sync agent."""
        self.running = False
        logger.info("Arrêt du SyncAgent demandé...")


async def main():
    agent = SyncAgent()
    
    # Gérer le signal d'arrêt (ex: via aitao.sh stop)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(agent)))

    await agent.start()

async def shutdown(agent):
    agent.stop()
    # Petit délai pour laisser le temps de cleanup si besoin
    await asyncio.sleep(1)
    sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
