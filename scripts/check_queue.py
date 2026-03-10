#!/usr/bin/env python3
"""Check queue status for a specific document."""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_config

def main():
    search = sys.argv[1] if len(sys.argv) > 1 else "CV Philippe BERTIERI"
    
    cfg = get_config()
    queue_dir = Path(cfg.get('paths.queue_dir'))
    queue_db = queue_dir / 'queue.db'
    
    print(f"Queue dir: {queue_dir}")
    print(f"DB exists: {queue_db.exists()}")
    
    if not queue_db.exists():
        print("Queue database does not exist")
        return
    
    conn = sqlite3.connect(queue_db)
    cur = conn.cursor()
    
    # Search
    cur.execute(
        "SELECT path, status, error, created_at FROM tasks WHERE path LIKE ?",
        (f"%{search}%",)
    )
    rows = cur.fetchall()
    
    if rows:
        print(f"\nFound {len(rows)} match(es):")
        for path, status, error, created in rows:
            print(f"  Path: {path}")
            print(f"  Status: {status}")
            print(f"  Error: {error}")
            print(f"  Created: {created}")
            print()
    else:
        print(f"\nNo matches for '{search}'")
    
    # Stats
    cur.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    print("\nQueue stats:")
    for status, count in cur.fetchall():
        print(f"  {status}: {count}")
    
    conn.close()

if __name__ == "__main__":
    main()
