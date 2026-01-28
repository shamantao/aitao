import sys
import os
try:
    import src.core.kotaemon_indexer as k
    print(f"Loaded kotaemon_indexer from: {k.__file__}")
except ImportError as e:
    print(f"ImportError: {e}")
    # Try adding current dir
    sys.path.append(os.getcwd())
    try:
        import src.core.kotaemon_indexer as k
        print(f"Loaded kotaemon_indexer from: {k.__file__}")
    except ImportError as e:
        print(f"Retry ImportError: {e}")
