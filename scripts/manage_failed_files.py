#!/usr/bin/env python3
"""
AI Tao - Failed Files CLI Tool

Command-line interface to manage failed indexations.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from core.kotaemon_indexer import AITaoIndexer
from core.logger import get_logger

logger = get_logger(__name__)


def show_stats(indexer: AITaoIndexer):
    """Display statistics about failed files."""
    stats = indexer.get_stats()
    failed_stats = stats.get('failed_files', {})
    
    print("\n📊 Statistiques d'indexation")
    print(f"   Documents indexés: {stats['document_count']}")
    print(f"   Collection: {stats.get('collection', 'default')}")
    
    print("\n❌ Fichiers échoués")
    print(f"   Total: {failed_stats.get('total_failed', 0)}")
    print(f"   Retryables (< 3 tentatives): {failed_stats.get('retryable', 0)}")
    
    by_reason = failed_stats.get('by_reason', {})
    if by_reason:
        print("\n   Par raison:")
        for reason, count in by_reason.items():
            print(f"   - {reason}: {count}")


def list_failed(indexer: AITaoIndexer, max_retries: int = 3):
    """List all failed files with details."""
    failed = indexer.failed_tracker.get_failed_files(max_retries=max_retries)
    
    if not failed:
        print("\n✅ Aucun fichier échoué")
        return
    
    print(f"\n❌ {len(failed)} fichier(s) échoué(s):\n")
    
    for file_path, info in failed.items():
        filename = Path(file_path).name
        reason = info.get('reason', 'unknown')
        retry_count = info.get('retry_count', 0)
        file_size = info.get('file_size', 0)
        sha256 = info.get('sha256', 'N/A')
        error = info.get('error', '')
        
        print(f"📄 {filename}")
        print(f"   Chemin: {file_path}")
        print(f"   Raison: {reason}")
        print(f"   Tentatives: {retry_count}")
        print(f"   Taille: {file_size} bytes")
        print(f"   SHA256: {sha256[:16]}..." if sha256 != 'N/A' else "   SHA256: N/A")
        print(f"   Erreur: {error[:100]}..." if len(error) > 100 else f"   Erreur: {error}")
        print()


def retry_failed(indexer: AITaoIndexer, max_retries: int = 3):
    """Retry failed files indexation."""
    result = indexer.retry_failed_files(max_retries=max_retries)
    
    print(f"\n🔄 Réessai d'indexation")
    print(f"   Réessayés: {result['retried']}")
    print(f"   Succès: {result['succeeded']}")
    print(f"   Échoués: {result['failed']}")
    
    if result['retried'] == 0:
        print("\n✅ Aucun fichier à réessayer")
    elif result['succeeded'] == result['retried']:
        print("\n✅ Tous les fichiers ont été indexés avec succès!")
    elif result['succeeded'] > 0:
        print(f"\n⚠️  {result['failed']} fichier(s) ont encore échoué")
    else:
        print("\n❌ Tous les fichiers ont échoué à nouveau")


def export_failed(indexer: AITaoIndexer, output_file: str):
    """Export failed files list to a file."""
    import json
    
    failed = indexer.failed_tracker.get_failed_files(max_retries=10)
    
    if not failed:
        print("\n✅ Aucun fichier échoué à exporter")
        return
    
    # Format for export
    export_data = []
    for file_path, info in failed.items():
        export_data.append({
            'path': file_path,
            'filename': Path(file_path).name,
            'reason': info.get('reason', 'unknown'),
            'retry_count': info.get('retry_count', 0),
            'file_size': info.get('file_size', 0),
            'sha256': info.get('sha256', ''),
            'error': info.get('error', ''),
            'timestamp': info.get('timestamp', '')
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {len(export_data)} fichier(s) échoué(s) exporté(s) vers: {output_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Tao - Gestion des fichiers échoués",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s stats                    # Afficher les statistiques
  %(prog)s list                     # Lister les fichiers échoués
  %(prog)s retry                    # Réessayer l'indexation
  %(prog)s export failed.json       # Exporter la liste en JSON
"""
    )
    
    parser.add_argument(
        'command',
        choices=['stats', 'list', 'retry', 'export'],
        help="Commande à exécuter"
    )
    
    parser.add_argument(
        'output',
        nargs='?',
        help="Fichier de sortie (pour 'export')"
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help="Nombre maximum de tentatives (défaut: 3)"
    )
    
    args = parser.parse_args()
    
    # Initialize indexer
    try:
        indexer = AITaoIndexer(collection_name="default")
    except Exception as e:
        print(f"\n❌ Erreur d'initialisation: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'stats':
            show_stats(indexer)
        
        elif args.command == 'list':
            list_failed(indexer, max_retries=args.max_retries)
        
        elif args.command == 'retry':
            retry_failed(indexer, max_retries=args.max_retries)
        
        elif args.command == 'export':
            if not args.output:
                print("\n❌ Erreur: spécifiez un fichier de sortie")
                print("Exemple: ./aitao.sh failed export failed.json")
                sys.exit(1)
            export_failed(indexer, args.output)
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
