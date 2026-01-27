#!/usr/bin/env python3
"""
Benchmark Indexing - Measure scan, OCR and indexing performance

Responsibilities:
- Time full indexing pipeline
- Track OCR engine usage
- Measure throughput (files/sec)
- Generate statistics report
- Store metrics for comparison
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.core.kotaemon_indexer import AITaoIndexer
from src.core.path_manager import path_manager
from src.core.logger import get_logger

logger = get_logger("BenchmarkIndexing", "benchmark_indexing.log")


def count_files(folder: Path, exts: set) -> int:
    """Count files with specified extensions."""
    count = 0
    for root, _, files in os.walk(folder):
        for f in files:
            if Path(f).suffix.lower() in exts:
                count += 1
    return count


def benchmark_indexing(folder: Path) -> dict:
    """Run indexing benchmark and return metrics."""
    logger.info("=" * 70)
    logger.info("📊 AI TAO - BENCHMARK INDEXATION")
    logger.info("=" * 70)
    logger.info(f"📂 Dossier: {folder}")
    
    # Supported extensions
    exts = {".txt", ".md", ".pdf", ".json", ".html", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    
    # Count files
    logger.info("\n🔍 Analyse du dossier...")
    total_files = count_files(folder, exts)
    logger.info(f"📄 {total_files} fichier(s) à traiter")
    
    # Initialize indexer
    logger.info("\n🔧 Initialisation indexeur...")
    init_start = time.time()
    indexer = AITaoIndexer(collection_name="default")
    init_time = time.time() - init_start
    logger.info(f"✅ Indexeur prêt en {init_time:.2f}s")
    
    if not indexer.is_enabled():
        logger.error("❌ Indexeur non disponible")
        return {}
    
    # Start indexing
    logger.info("\n⏳ Démarrage indexation...")
    index_start = time.time()
    
    indexed_count = indexer.index_folder(folder, recursive=True, exts=exts)
    
    index_time = time.time() - index_start
    total_time = init_time + index_time
    
    # Get stats
    stats = indexer.get_stats()
    doc_count = stats.get("document_count", 0)
    failed_stats = stats.get("failed_files", {})
    
    # Calculate metrics
    throughput = indexed_count / index_time if index_time > 0 else 0
    success_rate = (indexed_count / total_files * 100) if total_files > 0 else 0
    
    # Collect results
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "folder": str(folder),
        "total_files": total_files,
        "indexed_files": indexed_count,
        "failed_files": total_files - indexed_count,
        "success_rate_pct": round(success_rate, 2),
        "init_time_sec": round(init_time, 2),
        "index_time_sec": round(index_time, 2),
        "total_time_sec": round(total_time, 2),
        "throughput_files_per_sec": round(throughput, 2),
        "db_document_count": doc_count,
        "failed_by_reason": failed_stats.get("by_reason", {}),
    }
    
    # Display results
    logger.info("\n" + "=" * 70)
    logger.info("📊 RÉSULTATS BENCHMARK")
    logger.info("=" * 70)
    logger.info(f"✅ Fichiers indexés: {indexed_count}/{total_files} ({success_rate:.1f}%)")
    logger.info(f"⏱️  Temps init: {init_time:.2f}s")
    logger.info(f"⏱️  Temps indexation: {index_time:.2f}s")
    logger.info(f"⏱️  Temps total: {total_time:.2f}s")
    logger.info(f"🚀 Débit: {throughput:.1f} fichiers/sec")
    logger.info(f"📄 Documents en base: {doc_count}")
    
    if failed_stats.get("by_reason"):
        logger.info("\n⚠️  Échecs par raison:")
        for reason, count in failed_stats.get("by_reason", {}).items():
            logger.info(f"   • {reason}: {count}")
    
    logger.info("\n" + "=" * 70)
    
    return metrics


def save_metrics(metrics: dict, output_file: Path) -> None:
    """Save metrics to JSON file."""
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    
    history.append(metrics)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Statistiques sauvegardées: {output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark AI Tao indexing performance")
    parser.add_argument(
        "--folder",
        type=str,
        help="Folder to index (default: from config include_paths[0])"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs/benchmark_history.json",
        help="Output file for metrics (default: logs/benchmark_history.json)"
    )
    
    args = parser.parse_args()
    
    # Get folder
    if args.folder:
        folder = Path(args.folder)
    else:
        config = path_manager.get_indexing_config()
        paths = config.get("include_paths", [])
        if not paths:
            logger.error("❌ Aucun chemin configuré")
            sys.exit(1)
        folder = Path(paths[0])
    
    if not folder.exists():
        logger.error(f"❌ Dossier inexistant: {folder}")
        sys.exit(1)
    
    # Run benchmark
    metrics = benchmark_indexing(folder)
    
    if metrics:
        # Save metrics
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        save_metrics(metrics, output_file)
        
        logger.info("\n✅ BENCHMARK TERMINÉ")
    else:
        sys.exit(1)
