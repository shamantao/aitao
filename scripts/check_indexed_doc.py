#!/usr/bin/env python3
"""
Check if a document is indexed in LanceDB.

Usage:
    python scripts/check_indexed_doc.py "/path/to/document.pdf"
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.search.lancedb_client import LanceDBClient


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_indexed_doc.py <path>")
        sys.exit(1)
    
    search_path = sys.argv[1]
    search_name = Path(search_path).stem
    
    print("=" * 60)
    print(f"Checking: {search_name}")
    print("=" * 60)
    
    client = LanceDBClient()
    table = client.db.open_table(client.table_name)
    df = table.to_pandas()
    
    print(f"\nTotal documents in index: {len(df)}")
    
    # Search by exact path
    exact = df[df['path'] == search_path]
    if len(exact) > 0:
        print("\n[OK] Document found (exact match):")
        show_doc(exact.iloc[0])
        return
    
    # Search by partial path
    partial = df[df['path'].str.contains(search_name, case=False, na=False)]
    if len(partial) > 0:
        print(f"\n[OK] Document found (partial match on '{search_name}'):")
        show_doc(partial.iloc[0])
        return
    
    # Not found
    print(f"\n[X] Document NOT FOUND in index")
    print(f"\nSearched for: {search_path}")
    print(f"\nChecking if file exists...")
    
    if Path(search_path).exists():
        print(f"  File EXISTS on disk")
        print(f"  Size: {Path(search_path).stat().st_size} bytes")
        
        # Check if in indexed paths
        from src.core.config import get_config
        cfg = get_config()
        include_paths = cfg.get("indexing.include_paths", [])
        print(f"\nIncluded paths in config:")
        for p in include_paths:
            print(f"  - {p}")
        
        # Check if path matches
        is_included = any(search_path.startswith(str(p)) for p in include_paths)
        if is_included:
            print(f"\n[!] File IS in an included path but not indexed!")
            print("    It may be queued for indexing or had an extraction error.")
        else:
            print(f"\n[!] File is NOT in any included path")
            print("    Add its directory to indexing.include_paths in config.yaml")
    else:
        print(f"  File does NOT exist on disk")


def show_doc(doc):
    """Display document details."""
    print(f"  Path: {doc['path']}")
    print(f"  Title: {doc['title']}")
    content = str(doc['content'])
    print(f"  Content length: {len(content)} chars")
    if len(content) == 0:
        print("  Content: EMPTY (no text extracted)")
    else:
        print(f"  Content preview:")
        # Show first 500 chars
        preview = content[:500].replace('\n', ' ')
        print(f"    {preview}...")


if __name__ == "__main__":
    main()
