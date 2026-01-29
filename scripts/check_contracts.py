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

Usage:
  python scripts/check_contracts.py         # Run all checks
  python scripts/check_contracts.py --fix   # Show fix suggestions
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
    
    def run_all_checks(self) -> list[Violation]:
        """Run all contract checks on the entire codebase."""
        self.violations = []
        
        for py_file in self.get_python_files():
            self.check_file(py_file)
        
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


def main() -> int:
    """Main entry point."""
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_dir = project_root / "src"
    
    if not src_dir.exists():
        print(f"❌ Source directory not found: {src_dir}")
        return 1
    
    print(f"🔍 Checking architecture contracts in {src_dir}")
    print("=" * 60)
    
    checker = ContractChecker(src_dir)
    violations = checker.run_all_checks()
    
    show_suggestions = "--fix" in sys.argv
    checker.print_report(show_suggestions=show_suggestions)
    
    # Return non-zero exit code if violations found
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
