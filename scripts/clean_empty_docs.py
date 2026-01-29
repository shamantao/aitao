#!/usr/bin/env python3
"""
Clean Empty Documents from LanceDB Index

This script removes documents with empty content from the LanceDB vector index.
These documents were indexed before the content validation was added and cause
poor search results (they have zero-vector embeddings).

Usage:
    python scripts/clean_empty_docs.py           # Dry run (shows what would be deleted)
    python scripts/clean_empty_docs.py --apply   # Actually delete empty documents
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.search.lancedb_client import LanceDBClient


def main():
    parser = argparse.ArgumentParser(
        description="Clean empty documents from LanceDB index"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete empty documents (default: dry run)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("LanceDB Empty Document Cleaner")
    print("=" * 60)
    
    client = LanceDBClient()
    
    # Get all documents
    table = client.db.open_table(client.table_name)
    df = table.to_pandas()
    
    print(f"\nTotal documents in index: {len(df)}")
    
    # Find documents with empty content
    empty_mask = df['content'].apply(lambda x: not x or not str(x).strip())
    empty_docs = df[empty_mask]
    
    print(f"Documents with empty content: {len(empty_docs)}")
    
    if len(empty_docs) == 0:
        print("\n✅ No empty documents found - index is clean!")
        return
    
    print("\nEmpty documents found:")
    print("-" * 60)
    for _, doc in empty_docs.iterrows():
        print(f"  - {doc['title'][:50]}")
        print(f"    Path: {doc['path']}")
        print(f"    ID: {doc['id'][:16]}...")
        print()
    
    if not args.apply:
        print("\n⚠️  DRY RUN - No documents deleted")
        print("    Run with --apply to delete these documents")
        return
    
    # Delete empty documents
    print("\n🗑️  Deleting empty documents...")
    deleted = 0
    for _, doc in empty_docs.iterrows():
        doc_id = doc['id']
        try:
            client.delete(doc_id)
            deleted += 1
            print(f"  ✓ Deleted: {doc['title'][:40]}")
        except Exception as e:
            print(f"  ✗ Failed to delete {doc_id[:16]}...: {e}")
    
    print(f"\n✅ Deleted {deleted} empty documents")
    
    # Verify
    df_after = table.to_pandas()
    print(f"   Documents remaining: {len(df_after)}")


if __name__ == "__main__":
    main()
