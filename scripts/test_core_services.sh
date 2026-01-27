#!/bin/bash

# Test AI Tao Core Services (without Docker UI)
# Tests: API Server, RAG Server, and SyncAgent

set -e

PROJECT_ROOT="/Users/phil/Library/CloudStorage/Dropbox/devwww/AI-model/aitao"
cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "=================================="
echo "🧪 Testing AI Tao Core Services"
echo "=================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: RAG Server imports
echo ""
echo -e "${BLUE}Test 1: RAG Server - Can import and create app${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
from src.core.rag_server import app, RAGServer
print('✅ RAG Server imports OK')
print(f'✅ Routes: {[str(r.path) for r in app.routes[:3]]}')
" 2>&1; then
    echo -e "${GREEN}✅ PASS: RAG Server initialization${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: RAG Server import failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 2: Sync Agent imports
echo ""
echo -e "${BLUE}Test 2: Sync Agent - Can import and instantiate${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
from src.core.sync_agent import SyncAgent
print('✅ SyncAgent imports OK')
agent = SyncAgent()
print(f'✅ SyncAgent config paths: {len(agent.paths)} path(s)')
print(f'✅ Indexer enabled: {agent.indexer.is_enabled()}')
" 2>&1; then
    echo -e "${GREEN}✅ PASS: SyncAgent initialization${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: SyncAgent import failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Indexer functionality
echo ""
echo -e "${BLUE}Test 3: AITaoIndexer - Can instantiate and check status${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
from src.core.kotaemo_indexer import AITaoIndexer
indexer = AITaoIndexer()
print(f'✅ Indexer enabled: {indexer.is_enabled()}')
print(f'✅ Storage root: {indexer.storage_root}')
print(f'✅ Vector DB: {indexer.vector_db_path}')
" 2>&1; then
    echo -e "${GREEN}✅ PASS: AITaoIndexer initialization${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: AITaoIndexer init failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: RAG Engine
echo ""
echo -e "${BLUE}Test 4: RAG Engine - Can get stats${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
from src.core.rag import rag
stats = rag.get_stats()
print(f'✅ RAG Stats: {stats}')
" 2>&1; then
    echo -e "${GREEN}✅ PASS: RAG Engine get_stats() works${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: RAG Engine get_stats() failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Path Manager
echo ""
echo -e "${BLUE}Test 5: PathManager - Configuration resolved${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
from src.core.path_manager import path_manager
print(f'✅ Storage root: {path_manager.get_storage_root()}')
print(f'✅ Logs dir: {path_manager.get_logs_dir()}')
print(f'✅ Vector DB: {path_manager.get_vector_db_path()}')
print(f'✅ Models dir: {path_manager.get_models_dir()}')
config = path_manager.get_indexing_config()
print(f'✅ Include paths: {len(config.get(\"include_paths\", []))} path(s)')
" 2>&1; then
    echo -e "${GREEN}✅ PASS: PathManager configuration${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: PathManager failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Check logs directory
echo ""
echo -e "${BLUE}Test 6: Logs - Directory exists and writable${NC}"
LOGS_DIR="/Users/phil/Downloads/_sources/aitao/logs"
if [ -d "$LOGS_DIR" ] && [ -w "$LOGS_DIR" ]; then
    echo -e "${GREEN}✅ PASS: Logs directory OK ($LOGS_DIR)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: Logs directory issue${NC}"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo "=================================="
echo "📊 Core Services Test Results"
echo "=================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✨ All core services tested successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start API server:     cd $PROJECT_ROOT && python3 -m src.core.server"
    echo "  2. Start RAG server:     cd $PROJECT_ROOT && python3 -m src.core.rag_server"
    echo "  3. Start Sync Agent:     cd $PROJECT_ROOT && python3 -m src.core.sync_agent"
    echo "  4. Or use orchestrator:  ./aitao.sh start (requires Docker)"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review above.${NC}"
    exit 1
fi
