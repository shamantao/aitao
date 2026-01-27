#!/usr/bin/env python3
"""
RAG Admin Dashboard - AI Tao

Simple Gradio interface to manage RAG system:
- View indexation statistics
- Monitor failed files
- Retry failed indexations
- Trigger manual re-indexation
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import gradio as gr
from datetime import datetime

from core.kotaemon_indexer import AITaoIndexer
from core.logger import get_logger
from core.path_manager import PathManager

logger = get_logger(__name__)


class RAGDashboard:
    """Admin dashboard for RAG system monitoring."""
    
    def __init__(self):
        """Initialize dashboard."""
        self.indexer = AITaoIndexer(collection_name="default")
        self.pm = PathManager()
    
    def get_stats_summary(self) -> str:
        """Get formatted statistics summary."""
        stats = self.indexer.get_stats()
        
        summary = f"""
## 📊 Statistiques d'indexation

**Documents indexés:** {stats['document_count']}  
**Collection:** {stats.get('collection', 'default')}

### ❌ Fichiers échoués

**Total échoués:** {stats.get('failed_files', {}).get('total_failed', 0)}  
**Retryables (< 3 tentatives):** {stats.get('failed_files', {}).get('retryable', 0)}

#### Par catégorie:
"""
        by_reason = stats.get('failed_files', {}).get('by_reason', {})
        if by_reason:
            for reason, count in by_reason.items():
                summary += f"- **{reason}:** {count}\n"
        else:
            summary += "*Aucun échec*\n"
        
        return summary
    
    def get_failed_files_table(self) -> list:
        """Get failed files as table data."""
        failed = self.indexer.failed_tracker.get_failed_files(max_retries=10)
        
        if not failed:
            return []
        
        table_data = []
        for file_path, info in failed.items():
            table_data.append([
                Path(file_path).name,
                info.get('reason', 'unknown'),
                info.get('retry_count', 0),
                info.get('file_size', 0),
                info.get('sha256', '')[:16] + '...' if info.get('sha256') else 'N/A',
                info.get('error', '')[:50] + '...' if len(info.get('error', '')) > 50 else info.get('error', '')
            ])
        
        return table_data
    
    def retry_failed_files(self, max_retries: int = 3) -> str:
        """Retry failed files indexation."""
        try:
            result = self.indexer.retry_failed_files(max_retries=max_retries)
            
            if result['retried'] == 0:
                return "✅ Aucun fichier à réessayer"
            
            return f"""
✅ Réessai terminé:
- **Réessayés:** {result['retried']}
- **Succès:** {result['succeeded']}
- **Échoués:** {result['failed']}
"""
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return f"❌ Erreur: {str(e)}"
    
    def index_folder(self, folder_path: str, recursive: bool = True) -> str:
        """Manually index a folder."""
        try:
            if not folder_path:
                return "❌ Veuillez spécifier un chemin de dossier"
            
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                return f"❌ Dossier introuvable: {folder_path}"
            
            logger.info(f"Manual indexation: {folder_path}")
            self.indexer.index_folder(folder, recursive=recursive)
            
            stats = self.indexer.get_stats()
            return f"✅ Indexation terminée\n📄 Total documents: {stats['document_count']}"
        
        except Exception as e:
            logger.error(f"Manual indexation failed: {e}")
            return f"❌ Erreur: {str(e)}"


def create_dashboard() -> gr.Blocks:
    """Create Gradio dashboard interface."""
    dashboard = RAGDashboard()
    
    with gr.Blocks(title="AI Tao - RAG Admin", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🎛️ AI Tao - RAG Admin Dashboard")
        gr.Markdown("*Gestion de l'indexation et des fichiers échoués*")
        
        with gr.Tab("📊 Statistiques"):
            stats_output = gr.Markdown(value=dashboard.get_stats_summary())
            refresh_btn = gr.Button("🔄 Rafraîchir", variant="secondary")
            refresh_btn.click(
                fn=dashboard.get_stats_summary,
                outputs=stats_output
            )
        
        with gr.Tab("❌ Fichiers échoués"):
            gr.Markdown("### Liste des fichiers qui n'ont pas pu être indexés")
            
            failed_table = gr.Dataframe(
                headers=["Fichier", "Raison", "Tentatives", "Taille", "SHA256", "Erreur"],
                value=dashboard.get_failed_files_table(),
                interactive=False
            )
            
            with gr.Row():
                max_retries_input = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=3,
                    step=1,
                    label="Max tentatives"
                )
                retry_btn = gr.Button("🔄 Réessayer l'indexation", variant="primary")
            
            retry_output = gr.Markdown()
            
            retry_btn.click(
                fn=dashboard.retry_failed_files,
                inputs=max_retries_input,
                outputs=retry_output
            ).then(
                fn=dashboard.get_failed_files_table,
                outputs=failed_table
            )
        
        with gr.Tab("📁 Indexation manuelle"):
            gr.Markdown("### Indexer un dossier manuellement")
            
            with gr.Row():
                folder_input = gr.Textbox(
                    label="Chemin du dossier",
                    placeholder="/Users/phil/Downloads/_Volumes",
                    scale=3
                )
                recursive_checkbox = gr.Checkbox(
                    label="Récursif",
                    value=True,
                    scale=1
                )
            
            index_btn = gr.Button("🚀 Lancer l'indexation", variant="primary")
            index_output = gr.Markdown()
            
            index_btn.click(
                fn=dashboard.index_folder,
                inputs=[folder_input, recursive_checkbox],
                outputs=index_output
            )
            
            gr.Markdown("""
#### 💡 Exemples de chemins:
- `/Users/phil/Downloads/_Volumes`
- `/Users/phil/Documents`
- `/Users/phil/Desktop/test`
""")
        
        with gr.Tab("ℹ️ À propos"):
            gr.Markdown("""
## AI Tao - RAG Admin Dashboard

**Fonctionnalités:**
- 📊 Visualiser les statistiques d'indexation
- ❌ Monitorer les fichiers qui échouent
- 🔄 Réessayer l'indexation des fichiers échoués
- 📁 Indexer manuellement des dossiers
- 🔍 Voir les détails des erreurs (SHA256, taille, raison)

**Architecture:**
- **Vector DB:** LanceDB
- **Embeddings:** all-MiniLM-L6-v2 (local, multilingue)
- **Storage:** `{storage_root}/lancedb`
- **Failed Files:** `{storage_root}/failed_files.json`

**Note:** Les fichiers échoués sont conservés avec leur SHA256 pour vérification d'intégrité.
Vous pouvez les réessayer à tout moment ou les indexer manuellement après correction.
""")
    
    return app


def main():
    """Launch dashboard."""
    logger.info("🎛️ Starting RAG Admin Dashboard...")
    
    app = create_dashboard()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
