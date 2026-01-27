#!/bin/bash

# Test Critical Bug Fixes - January 27, 2026
# Tests: BUG-SYNC-001, BUG-RAG-001, BUG-AITAO-001

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================="
echo "🔬 Testing Critical Bug Fixes"
echo "=================================="

cd "$PROJECT_ROOT"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: BUG-AITAO-001 - check scan command
echo ""
echo -e "${BLUE}Test 1: BUG-AITAO-001 - ./aitao.sh check scan${NC}"
if output=$(./aitao.sh check scan 2>&1); then
    if [[ $output == *"chemin"* ]] || [[ $output == *"config"* ]]; then
        echo -e "${GREEN}✅ PASS: check scan command works${NC}"
        echo "Output: $output" | head -3
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL: check scan returned output but unexpected format${NC}"
        echo "Output: $output"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}❌ FAIL: check scan command crashed${NC}"
    echo "Error: $output"
    ((TESTS_FAILED++))
fi

# Test 2: BUG-RAG-001 - Python syntax check for rag.py
echo ""
echo -e "${BLUE}Test 2: BUG-RAG-001 - Verify rag.py syntax${NC}"
if python3 -m py_compile src/core/rag.py 2>&1; then
    echo -e "${GREEN}✅ PASS: rag.py compiles without errors${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: rag.py has syntax errors${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: BUG-RAG-001 - Check if PERSIST_DIR is fixed
echo ""
echo -e "${BLUE}Test 3: BUG-RAG-001 - Check PERSIST_DIR variable is fixed${NC}"
if grep -q "self.persist_dir" src/core/rag.py; then
    if ! grep -q "PERSIST_DIR" src/core/rag.py; then
        echo -e "${GREEN}✅ PASS: PERSIST_DIR variable fixed to self.persist_dir${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL: PERSIST_DIR still present in rag.py${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}❌ FAIL: self.persist_dir not found in rag.py${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: BUG-SYNC-001 - Check if index_folder is replaced
echo ""
echo -e "${BLUE}Test 4: BUG-SYNC-001 - Check index_folder method call fixed${NC}"
if grep -q "index_files" src/core/sync_agent.py; then
    if ! grep -q "index_folder" src/core/sync_agent.py; then
        echo -e "${GREEN}✅ PASS: index_folder call fixed to index_files${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL: index_folder still present in sync_agent.py${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}❌ FAIL: index_files not found in sync_agent.py${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: BUG-SYNC-001 - Python syntax check for sync_agent.py
echo ""
echo -e "${BLUE}Test 5: BUG-SYNC-001 - Verify sync_agent.py syntax${NC}"
if python3 -m py_compile src/core/sync_agent.py 2>&1; then
    echo -e "${GREEN}✅ PASS: sync_agent.py compiles without errors${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: sync_agent.py has syntax errors${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Check that imports work
echo ""
echo -e "${BLUE}Test 6: Verify imports work${NC}"
if python3 -c "from src.core.path_manager import path_manager; print('✅ path_manager imports OK')" 2>&1; then
    echo -e "${GREEN}✅ PASS: path_manager imports correctly${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL: path_manager import failed${NC}"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo "=================================="
echo "📊 Test Results"
echo "=================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✨ All critical bug fixes verified!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review above.${NC}"
    exit 1
fi
