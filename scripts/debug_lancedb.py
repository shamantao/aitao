import lancedb

db = lancedb.connect("/Users/phil/Downloads/_sources/aitao/lancedb")
try:
    tbl = db.open_table("default")
    # Get all rows
    rows = tbl.search().limit(1000).to_list()
    print(f"Total rows: {len(rows)}")
    print("Files indexed:")
    paths = [r['path'] for r in rows]
    for path in sorted(paths):
        print(path)
except Exception as e:
    print(f"Error: {e}")
