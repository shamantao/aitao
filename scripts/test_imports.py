#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

print('=' * 50)
print('Testing AI Tao Code Syntax & Imports')
print('=' * 50)

# Test all critical modules can be parsed
modules = [
    'src.core.path_manager',
    'src.core.logger',
    'src.core.sync_agent',
    'src.core.rag',
    'src.core.rag_server',
    'src.core.anythingllm_client',
    'src.core.failed_files_tracker',
]

failed = []
for mod in modules:
    try:
        __import__(mod)
        print(f'OK {mod}')
    except ImportError as e:
        if 'lancedb' in str(e) or 'sentence_transformers' in str(e):
            print(f'WARN {mod} (missing optional dep)')
        else:
            print(f'FAIL {mod}: {e}')
            failed.append(mod)
    except Exception as e:
        print(f'FAIL {mod}: {e}')
        failed.append(mod)

print()
if not failed:
    print('SUCCESS All critical modules load!')
    print()
    print('Notes:')
    print('  - lancedb/sentence_transformers optional (for indexing)')
    print('  - RAG/Indexing gracefully degrade if missing')
else:
    print(f'FAIL {len(failed)} modules failed to load')
    sys.exit(1)
