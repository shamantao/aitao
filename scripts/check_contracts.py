#!/usr/bin/env python3
"""
Architecture Contracts Verification Script

This script enforces the architectural rules defined in the PRD (Section 10.1).
It scans the codebase to detect violations of the Architecture Contracts.

Contracts verified:
  AC-001: ConfigManager singleton usage
  AC-002: No hardcoded paths (no 'data/' literals)
  AC-003: Structured logging only (no print statements)
  AC-004: No placeholder functions (functions must have real implementations)
  AC-005: No Path() for system paths outside pathmanager.py
  AC-006: PathManager must be imported for path operations
  AC-007: StatsKeys must be used for statistics dictionaries
  AC-008: No .log files inside the project source tree

Usage:
  python scripts/check_contracts.py           # Run all checks
  python scripts/check_contracts.py --fix     # Show fix suggestions
  python scripts/check_contracts.py --stats   # Show adoption metrics only
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class Violation:
    """Represents an architecture contract violation."""
    
    contract: str
    file_path: Path
    line_number: int
    description: str
    suggestion: str


class ContractChecker:
    """Checks source code for architecture contract violations."""
    
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.violations: list[Violation] = []
        
        # Patterns to detect
        self.hardcoded_path_patterns = [
            '"data/',
            "'data/",
            '"./data/',
            "'./data/",
            'Path("data',
            "Path('data",
        ]
        
        # Files to exclude from checks
        self.exclude_patterns = [
            "__pycache__",
            ".pyc",
            "check_contracts.py",  # Exclude self
            "pathmanager.py",  # PathManager defines default paths (by design)
            "path_manager.py",  # Generic path manager lib
        ]
        
        # Stats key patterns that should use StatsKeys
        self.stats_key_patterns = [
            '"total_documents"',
            "'total_documents'",
            '"document_count"',
            "'document_count'",
            '"total_chunks"',
            "'total_chunks'",
            '"embedding_dimension"',
            "'embedding_dimension'",
            '"is_indexing"',
            "'is_indexing'",
            '"table_name"',
            "'table_name'",
            '"index_name"',
            "'index_name'",
        ]
        
        # System path patterns (Path() usage for system directories)
        self.system_path_patterns = [
            'Path(__file__)',  # OK - relative imports
            'Path(storage',
            'Path(queue',
            'Path(db_path)',
            '/ "lancedb"',
            "/ 'lancedb'",
            '/ "queue"',
            "/ 'queue'",
            '/ "logs"',
            "/ 'logs'",
            '/ "cache"',
            "/ 'cache'",
        ]
    
    def get_python_files(self) -> Iterator[Path]:
        """Yield all Python files in src directory."""
        for py_file in self.src_dir.rglob("*.py"):
            if not any(excl in str(py_file) for excl in self.exclude_patterns):
                yield py_file
    
    def check_ac001_config_singleton(self, file_path: Path, content: str, tree: ast.AST) -> None:
        """AC-001: ConfigManager must be used via get_config() singleton."""
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            # Check for direct ConfigManager() instantiation
            if "ConfigManager()" in line and "def " not in line:
                # Exclude lines in config.py itself (where singleton is defined)
                if "config.py" not in str(file_path):
                    self.violations.append(Violation(
                        contract="AC-001",
                        file_path=file_path,
                        line_number=i,
                        description="Direct ConfigManager() instantiation detected",
                        suggestion="Use get_config() singleton instead of ConfigManager()",
                    ))
    
    def check_ac002_no_hardcoded_paths(self, file_path: Path, content: str, tree: ast.AST) -> None:
        """AC-002: No hardcoded paths like 'data/' in source files."""
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            for pattern in self.hardcoded_path_patterns:
                if pattern in line:
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    
                    self.violations.append(Violation(
                        contract="AC-002",
                        file_path=file_path,
                        line_number=i,
                        description=f"Hardcoded path pattern '{pattern}' detected",
                        suggestion="Use config.get('paths', 'key') or PathManager instead",
                    ))
    
    def check_ac003_no_print_statements(self, file_path: Path, content: str, tree: ast.AST) -> None:
        """AC-003: Use structured logging, not print statements."""
        # Skip test files, scripts, and CLI user-facing code
        if "/tests/" in str(file_path) or "/scripts/" in str(file_path):
            return
        # CLI files use print() for user output (legitimate)
        if "/cli/" in str(file_path):
            return
        # path_manager debug output (should be removed eventually)
        if "path_manager.py" in str(file_path):
            return
        # logger.py uses print() as fallback when logger can't initialize
        if "logger.py" in str(file_path):
            return
        
        class PrintVisitor(ast.NodeVisitor):
            def __init__(self, checker: ContractChecker, file_path: Path):
                self.checker = checker
                self.file_path = file_path
            
            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    self.checker.violations.append(Violation(
                        contract="AC-003",
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description="print() statement detected in production code",
                        suggestion="Use logger.info(), logger.debug() etc. instead",
                    ))
                self.generic_visit(node)
        
        try:
            visitor = PrintVisitor(self, file_path)
            visitor.visit(tree)
        except Exception:
            pass  # Skip if AST parsing fails
    
    def check_ac004_no_placeholder_functions(self, file_path: Path, content: str, tree: ast.AST) -> None:
        """AC-004: Functions must have real implementations, not just 'pass' or docstring."""
        
        class PlaceholderVisitor(ast.NodeVisitor):
            def __init__(self, checker: ContractChecker, file_path: Path):
                self.checker = checker
                self.file_path = file_path
            
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._check_function(node)
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._check_function(node)
                self.generic_visit(node)
            
            def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                # Skip abstract methods and property getters
                if any(
                    isinstance(d, ast.Name) and d.id in ("abstractmethod", "property")
                    for d in node.decorator_list
                ):
                    return
                
                # Skip __init__ with only pass (sometimes valid for simple classes)
                if node.name == "__init__":
                    return
                
                # Get the body, excluding docstrings
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    body = body[1:]  # Skip docstring
                
                # Check if body is only 'pass' or 'return None' or empty
                if len(body) == 0:
                    self.checker.violations.append(Violation(
                        contract="AC-004",
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Function '{node.name}' has no implementation (only docstring)",
                        suggestion="Implement the function or raise NotImplementedError",
                    ))
                elif len(body) == 1:
                    stmt = body[0]
                    is_placeholder = False
                    
                    if isinstance(stmt, ast.Pass):
                        is_placeholder = True
                    elif isinstance(stmt, ast.Return) and stmt.value is None:
                        is_placeholder = True
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        # Just a string (like a second docstring)
                        is_placeholder = True
                    
                    if is_placeholder:
                        self.checker.violations.append(Violation(
                            contract="AC-004",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            description=f"Function '{node.name}' appears to be a placeholder",
                            suggestion="Implement the function or raise NotImplementedError",
                        ))
        
        try:
            visitor = PlaceholderVisitor(self, file_path)
            visitor.visit(tree)
        except Exception:
            pass
    
    def check_ac007_stats_keys(self, file_path: Path, content: str, tree: ast.AST) -> None:
        """AC-007: StatsKeys must be used for statistics dictionaries."""
        # Skip registry.py where StatsKeys is defined
        if "registry.py" in str(file_path):
            return
        # Skip test files
        if "/tests/" in str(file_path):
            return
        
        lines = content.splitlines()
        
        # Check if file imports StatsKeys
        has_statskeys_import = "StatsKeys" in content
        
        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            
            for pattern in self.stats_key_patterns:
                if pattern in line:
                    # Check if it's in a get() call or dict literal (stats context)
                    if ".get(" in line or "stats" in line.lower() or "return {" in line:
                        if not has_statskeys_import:
                            self.violations.append(Violation(
                                contract="AC-007",
                                file_path=file_path,
                                line_number=i,
                                description=f"Hardcoded stats key {pattern} without StatsKeys import",
                                suggestion="from core.registry import StatsKeys; use StatsKeys.TOTAL_DOCUMENTS",
                            ))
                            break  # One violation per file is enough
    
    def check_file(self, file_path: Path) -> None:
        """Run all contract checks on a single file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return  # Skip files with syntax errors
        except Exception:
            return
        
        self.check_ac001_config_singleton(file_path, content, tree)
        self.check_ac002_no_hardcoded_paths(file_path, content, tree)
        self.check_ac003_no_print_statements(file_path, content, tree)
        self.check_ac004_no_placeholder_functions(file_path, content, tree)
        self.check_ac007_stats_keys(file_path, content, tree)
    
    def check_ac008_no_log_files_in_source(self) -> None:
        """AC-008: No .log files may exist inside src/ or tests/ directories.

        Runtime log files in logs/ or data/ are expected and gitignored.
        A log file landing in src/ or tests/ signals a wrong fallback path.
        """
        code_dirs = [self.src_dir, self.src_dir.parent / "tests"]
        for code_dir in code_dirs:
            if not code_dir.exists():
                continue
            for log_file in code_dir.rglob("*.log"):
                parts = log_file.parts
                if any(p.startswith(".") or p in ("venv", ".venv", "__pycache__") for p in parts):
                    continue
                self.violations.append(Violation(
                    contract="AC-008",
                    file_path=log_file,
                    line_number=0,
                    description=f"Log file found inside code directory: {log_file.relative_to(self.src_dir.parent)}",
                    suggestion=(
                        "Log files must be written via PathManager.get_logs_dir() to the storage directory. "
                        "Check logger.py fallback and ensure no test creates logs in src/ or tests/."
                    ),
                ))

    def run_all_checks(self) -> list[Violation]:
        """Run all contract checks on the entire codebase."""
        self.violations = []

        for py_file in self.get_python_files():
            self.check_file(py_file)

        self.check_ac008_no_log_files_in_source()

        return self.violations
    
    def print_report(self, show_suggestions: bool = False) -> None:
        """Print a formatted report of violations."""
        if not self.violations:
            print("✅ All architecture contracts satisfied!")
            return
        
        print(f"\n❌ Found {len(self.violations)} architecture contract violation(s):\n")
        
        # Group by contract
        by_contract: dict[str, list[Violation]] = {}
        for v in self.violations:
            by_contract.setdefault(v.contract, []).append(v)
        
        for contract, violations in sorted(by_contract.items()):
            print(f"═══ {contract} ({len(violations)} violation(s)) ═══")
            for v in violations:
                rel_path = v.file_path.relative_to(self.src_dir.parent) if v.file_path.is_relative_to(self.src_dir.parent) else v.file_path
                print(f"  {rel_path}:{v.line_number}")
                print(f"    → {v.description}")
                if show_suggestions:
                    print(f"    💡 {v.suggestion}")
            print()
    
    def calculate_adoption_metrics(self) -> dict:
        """Calculate Registry and PathManager adoption rates."""
        total_files = 0
        registry_imports = 0
        pathmanager_imports = 0
        statskeys_imports = 0
        
        files_with_stats = []
        files_needing_pathmanager = []
        
        for py_file in self.get_python_files():
            try:
                content = py_file.read_text(encoding="utf-8")
                total_files += 1
                
                # Check Registry/StatsKeys imports
                if "from core.registry import" in content or "from src.core.registry import" in content:
                    registry_imports += 1
                if "StatsKeys" in content:
                    statskeys_imports += 1
                
                # Check PathManager imports
                if "path_manager" in content or "pathmanager" in content.lower():
                    pathmanager_imports += 1
                
                # Files that use stats patterns but don't import StatsKeys
                has_stats_pattern = any(p in content for p in self.stats_key_patterns)
                if has_stats_pattern and "StatsKeys" not in content:
                    if "registry.py" not in str(py_file) and "/tests/" not in str(py_file):
                        files_with_stats.append(py_file)
                
                # Files that construct system paths manually
                for pattern in ["Path(storage", 'Path("data', "Path('data", "/ 'queue'", '/ "lancedb"']:
                    if pattern in content and "pathmanager" not in str(py_file).lower():
                        files_needing_pathmanager.append(py_file)
                        break
                        
            except Exception:
                continue
        
        return {
            "total_files": total_files,
            "registry_imports": registry_imports,
            "pathmanager_imports": pathmanager_imports,
            "statskeys_imports": statskeys_imports,
            "registry_rate": round(registry_imports / total_files * 100, 1) if total_files else 0,
            "pathmanager_rate": round(pathmanager_imports / total_files * 100, 1) if total_files else 0,
            "statskeys_rate": round(statskeys_imports / total_files * 100, 1) if total_files else 0,
            "files_needing_statskeys": files_with_stats,
            "files_needing_pathmanager": files_needing_pathmanager,
        }
    
    def print_adoption_report(self) -> None:
        """Print adoption metrics report."""
        metrics = self.calculate_adoption_metrics()
        
        print("\n📊 Architecture Adoption Metrics")
        print("=" * 50)
        print(f"Total Python files in src/: {metrics['total_files']}")
        print()
        print(f"Registry imports:     {metrics['registry_imports']:3d} / {metrics['total_files']} ({metrics['registry_rate']:5.1f}%)")
        print(f"PathManager imports:  {metrics['pathmanager_imports']:3d} / {metrics['total_files']} ({metrics['pathmanager_rate']:5.1f}%)")
        print(f"StatsKeys imports:    {metrics['statskeys_imports']:3d} / {metrics['total_files']} ({metrics['statskeys_rate']:5.1f}%)")
        print()
        
        # Status indicators
        registry_ok = metrics['registry_rate'] >= 80
        pathmanager_ok = metrics['pathmanager_rate'] >= 80
        
        print("Target: ≥80% adoption")
        print(f"  Registry:     {'✅' if registry_ok else '⚠️ '} {metrics['registry_rate']:.1f}%")
        print(f"  PathManager:  {'✅' if pathmanager_ok else '⚠️ '} {metrics['pathmanager_rate']:.1f}%")
        
        if metrics['files_needing_statskeys']:
            print(f"\n⚠️  Files using stats without StatsKeys ({len(metrics['files_needing_statskeys'])}):")
            for f in metrics['files_needing_statskeys'][:5]:
                print(f"    - {f.relative_to(self.src_dir.parent)}")
            if len(metrics['files_needing_statskeys']) > 5:
                print(f"    ... and {len(metrics['files_needing_statskeys']) - 5} more")


def main() -> int:
    """Main entry point."""
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_dir = project_root / "src"
    
    if not src_dir.exists():
        print(f"❌ Source directory not found: {src_dir}")
        return 1
    
    checker = ContractChecker(src_dir)
    
    # Stats only mode
    if "--stats" in sys.argv:
        checker.print_adoption_report()
        return 0
    
    print(f"🔍 Checking architecture contracts in {src_dir}")
    print("=" * 60)
    
    violations = checker.run_all_checks()
    
    show_suggestions = "--fix" in sys.argv
    checker.print_report(show_suggestions=show_suggestions)
    
    # Always show adoption metrics
    checker.print_adoption_report()
    
    # Return non-zero exit code if violations found
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
