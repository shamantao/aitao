#!/usr/bin/env python3
"""
System Compatibility Checker for AI Tao
Verifies that the host system meets requirements defined in config.toml
"""

import sys
import os
import platform
import socket
import shutil
from pathlib import Path
import importlib.util

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.path_manager import path_manager
except ImportError:
    print("❌ Cannot import path_manager. Run from project root.")
    sys.exit(1)


class SystemChecker:
    """
    Validates system compatibility with AI Tao configuration.
    """
    
    def __init__(self):
        self.config = path_manager.config
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_total = 0
    
    def check_python_version(self):
        """Check Python version (3.10+)"""
        self.checks_total += 1
        print("🐍 Checking Python version...", end=" ")
        
        version = sys.version_info
        if version.major == 3 and version.minor >= 10:
            print(f"✅ {version.major}.{version.minor}.{version.micro}")
            self.checks_passed += 1
        else:
            msg = f"Python 3.10+ required, found {version.major}.{version.minor}.{version.micro}"
            print(f"❌ {msg}")
            self.errors.append(msg)
    
    def check_ports_available(self):
        """Check if configured ports are available"""
        api_port = self.config.get("server", {}).get("api_port", 8247)
        ui_port = self.config.get("server", {}).get("ui_port", 3001)
        
        for port, name in [(api_port, "API"), (ui_port, "UI")]:
            self.checks_total += 1
            print(f"🔌 Checking port {port} ({name})...", end=" ")
            
            if self._is_port_available(port):
                print(f"✅ Available")
                self.checks_passed += 1
            else:
                msg = f"Port {port} ({name}) is already in use"
                print(f"⚠️  {msg}")
                self.warnings.append(msg)
    
    def _is_port_available(self, port):
        """Test if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False
    
    def check_storage_paths(self):
        """Check if storage paths are valid and writable"""
        storage_root = path_manager.get_storage_root()
        logs_dir = path_manager.get_logs_dir()
        
        paths_to_check = [
            (storage_root, "Storage Root"),
            (logs_dir, "Logs Directory")
        ]
        
        for path, name in paths_to_check:
            self.checks_total += 1
            print(f"📂 Checking {name} ({path})...", end=" ")
            
            try:
                path.mkdir(parents=True, exist_ok=True)
                
                # Test write permission
                test_file = path / ".aitao_write_test"
                test_file.touch()
                test_file.unlink()
                
                print(f"✅ OK")
                self.checks_passed += 1
            except Exception as e:
                msg = f"{name} not writable: {e}"
                print(f"❌ {msg}")
                self.errors.append(msg)
    
    def check_models_directory(self):
        """Check if models directory exists and contains models"""
        self.checks_total += 1
        models_dir = self.config.get("models", {}).get("models_dir")
        
        print(f"🤖 Checking models directory...", end=" ")
        
        if not models_dir:
            msg = "models_dir not configured in config.toml"
            print(f"❌ {msg}")
            self.errors.append(msg)
            return
        
        models_path = Path(models_dir)
        if not models_path.exists():
            msg = f"Models directory does not exist: {models_dir}"
            print(f"❌ {msg}")
            self.errors.append(msg)
            return
        
        # Check for .gguf files
        gguf_files = list(models_path.rglob("*.gguf"))
        if gguf_files:
            print(f"✅ Found {len(gguf_files)} model(s)")
            self.checks_passed += 1
        else:
            msg = f"No .gguf models found in {models_dir}"
            print(f"⚠️  {msg}")
            self.warnings.append(msg)
    
    def check_indexing_paths(self):
        """Check if indexing paths exist and are readable"""
        include_paths = self.config.get("indexing", {}).get("include_paths", [])
        
        if not include_paths:
            self.checks_total += 1
            msg = "No indexing paths configured"
            print(f"⚠️  {msg}")
            self.warnings.append(msg)
            return
        
        for path_str in include_paths:
            self.checks_total += 1
            path = Path(path_str)
            print(f"📁 Checking indexing path ({path})...", end=" ")
            
            if path.exists():
                if os.access(path, os.R_OK):
                    print(f"✅ Readable")
                    self.checks_passed += 1
                else:
                    msg = f"Path not readable: {path}"
                    print(f"❌ {msg}")
                    self.errors.append(msg)
            else:
                msg = f"Path does not exist: {path}"
                print(f"⚠️  {msg}")
                self.warnings.append(msg)
    
    def check_required_commands(self):
        """Check if required external commands are available"""
        required_commands = [
            ("docker", "Docker (for AnythingLLM UI)"),
        ]
        
        for cmd, description in required_commands:
            self.checks_total += 1
            print(f"🔧 Checking {description}...", end=" ")
            
            if shutil.which(cmd):
                print(f"✅ Found")
                self.checks_passed += 1
            else:
                msg = f"{description} not found in PATH"
                print(f"❌ {msg}")
                self.errors.append(msg)
    
    def check_python_dependencies(self):
        """Check if critical Python packages are installed"""
        required_packages = [
            ("toml", "TOML parser (for config)"),
            ("fastapi", "FastAPI (API server)"),
            ("llama_cpp", "llama-cpp-python (inference engine)"),
            ("lancedb", "LanceDB (vector database)"),
        ]
        
        for package, description in required_packages:
            self.checks_total += 1
            print(f"📦 Checking {description}...", end=" ")
            
            spec = importlib.util.find_spec(package)
            if spec is not None:
                print(f"✅ Installed")
                self.checks_passed += 1
            else:
                msg = f"{description} not installed"
                print(f"❌ {msg}")
                self.errors.append(msg)
    
    def check_disk_space(self):
        """Check available disk space for storage_root"""
        self.checks_total += 1
        storage_root = path_manager.get_storage_root()
        
        print(f"💾 Checking disk space...", end=" ")
        
        try:
            stat = shutil.disk_usage(storage_root)
            free_gb = stat.free / (1024**3)
            
            # Warn if less than 10GB free
            if free_gb < 10:
                msg = f"Low disk space: {free_gb:.1f}GB free (recommend >10GB)"
                print(f"⚠️  {msg}")
                self.warnings.append(msg)
            else:
                print(f"✅ {free_gb:.1f}GB available")
                self.checks_passed += 1
        except Exception as e:
            msg = f"Cannot check disk space: {e}"
            print(f"⚠️  {msg}")
            self.warnings.append(msg)
    
    def check_platform(self):
        """Check OS platform"""
        self.checks_total += 1
        print(f"🖥️  Checking platform...", end=" ")
        
        system = platform.system()
        if system == "Darwin":
            print(f"✅ macOS {platform.mac_ver()[0]}")
            self.checks_passed += 1
        elif system == "Linux":
            print(f"✅ Linux")
            self.checks_passed += 1
        elif system == "Windows":
            print(f"⚠️  Windows (limited support)")
            self.warnings.append("Windows support is experimental")
        else:
            msg = f"Unsupported platform: {system}"
            print(f"❌ {msg}")
            self.errors.append(msg)
    
    def run_all_checks(self):
        """Run all system checks"""
        print("=" * 60)
        print("☯️  AI Tao - System Compatibility Check")
        print("=" * 60)
        print()
        
        # Run checks
        self.check_platform()
        self.check_python_version()
        self.check_required_commands()
        self.check_python_dependencies()
        self.check_ports_available()
        self.check_storage_paths()
        self.check_models_directory()
        self.check_indexing_paths()
        self.check_disk_space()
        
        # Summary
        print()
        print("=" * 60)
        print(f"✅ Passed: {self.checks_passed}/{self.checks_total}")
        
        if self.warnings:
            print(f"⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.errors:
            print(f"❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   • {error}")
        
        print("=" * 60)
        
        # Exit code
        if self.errors:
            print("\n❌ System check FAILED. Please fix errors before running AI Tao.")
            return 1
        elif self.warnings:
            print("\n⚠️  System check passed with warnings. AI Tao may work with limitations.")
            return 0
        else:
            print("\n✅ System check PASSED. AI Tao is ready to run!")
            return 0


def main():
    """Entry point"""
    checker = SystemChecker()
    exit_code = checker.run_all_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
