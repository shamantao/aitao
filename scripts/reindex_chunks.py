#!/usr/bin/env python3
"""
Reindex documents with chunking for RAG.

This script reads existing documents from Meilisearch and creates
chunks in LanceDB for fine-grained RAG retrieval.

Usage:
    python scripts/reindex_chunks.py [--limit N] [--doc-id DOC_ID]
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.search.meilisearch_client import MeilisearchClient
from src.indexation.chunker import ChunkingPipeline
from src.indexation.chunk_store import ChunkStore

logger = get_logger("reindex_chunks")


def main():
    parser = argparse.ArgumentParser(description="Reindex documents with chunking")
    parser.add_argument("--limit", type=int, default=0, help="Max documents to process (0=all)")
    parser.add_argument("--doc-id", type=str, help="Process specific document ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Chunking Reindexation - AItao")
    print("=" * 60)
    
    # Initialize components
    print("\n[1/4] Initializing components...")
    config = ConfigManager()
    meili = MeilisearchClient()
    pipeline = ChunkingPipeline()
    store = ChunkStore()
    
    print(f"  - Meilisearch: OK")
    print(f"  - ChunkingPipeline: chunk_size={pipeline.config.chunk_size}, overlap={pipeline.config.chunk_overlap}")
    print(f"  - ChunkStore: dimension={store.dimension}")
    
    # Get documents from Meilisearch
    print("\n[2/4] Fetching documents from Meilisearch...")
    
    if args.doc_id:
        # Fetch specific document with full content
        doc = meili.get_document(args.doc_id)
        if doc:
            documents = [doc]
        else:
            print(f"  Document not found: {args.doc_id}")
            return 1
    else:
        # Fetch document IDs via search, then get full content
        limit = args.limit if args.limit > 0 else 1000
        search_results = meili.search("", limit=limit)
        
        # Get full documents (search only returns 500 chars)
        documents = []
        for sr in search_results:
            doc_id = sr.get("id")
            if doc_id:
                full_doc = meili.get_document(doc_id)
                if full_doc:
                    documents.append(full_doc)
    
    print(f"  Found {len(documents)} documents to process")
    
    if args.dry_run:
        print("\n[DRY RUN] Would process:")
        for doc in documents[:10]:
            title = doc.get("title", "N/A")[:50]
            content_len = len(doc.get("content", ""))
            est_chunks = max(1, content_len // (pipeline.config.chunk_size * 3))
            print(f"  - {title} ({content_len} chars, ~{est_chunks} chunks)")
        if len(documents) > 10:
            print(f"  ... and {len(documents) - 10} more")
        return 0
    
    # Process documents
    print("\n[3/4] Creating chunks...")
    total_chunks = 0
    success = 0
    errors = 0
    
    start_time = time.time()
    
    for i, doc in enumerate(documents):
        doc_id = doc.get("id", "")
        title = doc.get("title", "Unknown")[:40]
        content = doc.get("content", "")
        path = doc.get("path", "")
        
        if not content or len(content.strip()) < 100:
            print(f"  [{i+1}/{len(documents)}] SKIP (no content): {title}")
            continue
        
        try:
            # Delete existing chunks for this document
            store.delete_by_doc_id(doc_id)
            
            # Create new chunks
            result = pipeline.chunk_document(
                text=content,
                doc_id=doc_id,
                path=path,
                title=title,
                metadata={
                    "category": doc.get("category"),
                    "language": doc.get("language"),
                },
            )
            
            if result.success and result.chunks:
                # Store chunks
                count = store.add_chunks(result.chunks)
                total_chunks += count
                success += 1
                print(f"  [{i+1}/{len(documents)}] OK: {title} -> {count} chunks")
            else:
                print(f"  [{i+1}/{len(documents)}] FAIL: {title} - {result.error}")
                errors += 1
                
        except Exception as e:
            print(f"  [{i+1}/{len(documents)}] ERROR: {title} - {e}")
            errors += 1
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n[4/4] Summary")
    print("=" * 60)
    print(f"  Documents processed: {success + errors}")
    print(f"  Successful: {success}")
    print(f"  Errors: {errors}")
    print(f"  Total chunks created: {total_chunks}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Average: {elapsed/max(1,success+errors):.2f}s per document")
    print("=" * 60)
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
