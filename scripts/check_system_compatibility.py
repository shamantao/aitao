#!/usr/bin/env python3
"""
System Compatibility Checker for AI Tao

This script verifies that the host machine meets the requirements
defined in config.toml before starting the services.

Checks:
- Port availability (API and UI ports)
- Storage paths existence and permissions
- Required Python packages
- Docker availability
- Disk space
- Model files existence

Author: AI Tao Project
"""

import sys
import os
import socket
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from src.core.path_manager import path_manager
except ImportError:
    print("❌ Error: Cannot import path_manager. Run from project root.")
    sys.exit(1)


class CompatibilityChecker:
    """
    Checks system compatibility with AI Tao configuration.
    """
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.config = path_manager.config
        
    def check_port_available(self, port: int, service_name: str) -> bool:
        """
        Check if a port is available on the local machine.
        
        Args:
            port: Port number to check
            service_name: Human-readable service name
            
        Returns:
            True if port is available, False otherwise
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        
        try:
            # Try to bind to the port
            sock.bind(('0.0.0.0', port))
            sock.close()
            print(f"  ✅ Port {port} ({service_name}): Available")
            return True
        except OSError:
            # Port is already in use
            try:
                # Try to connect to see what's using it
                sock.connect(('127.0.0.1', port))
                sock.close()
                self.errors.append(f"Port {port} ({service_name}) is already in use")
                print(f"  ❌ Port {port} ({service_name}): Already in use")
            except:
                self.warnings.append(f"Port {port} ({service_name}) might be in use")
                print(f"  ⚠️  Port {port} ({service_name}): Status unknown")
            return False
    
    def check_storage_paths(self) -> bool:
        """Check if storage paths exist and are writable."""
        storage_root = path_manager.get_storage_root()
        logs_dir = path_manager.get_logs_dir()
        
        paths_ok = True
        
        # Check storage root
        if storage_root.exists():
            if os.access(storage_root, os.W_OK):
                print(f"  ✅ Storage root: {storage_root} (writable)")
            else:
                self.errors.append(f"Storage root {storage_root} is not writable")
                print(f"  ❌ Storage root: {storage_root} (not writable)")
                paths_ok = False
        else:
            # Will be created on startup, check parent directory
            parent = storage_root.parent
            if parent.exists() and os.access(parent, os.W_OK):
                print(f"  ⚠️  Storage root: {storage_root} (will be created)")
                self.warnings.append(f"Storage root {storage_root} will be created on startup")
            else:
                self.errors.append(f"Cannot create storage root {storage_root} (parent not writable)")
                print(f"  ❌ Storage root: {storage_root} (cannot create)")
                paths_ok = False
        
        # Check logs directory
        if logs_dir.exists():
            if os.access(logs_dir, os.W_OK):
                print(f"  ✅ Logs directory: {logs_dir} (writable)")
            else:
                self.errors.append(f"Logs directory {logs_dir} is not writable")
                print(f"  ❌ Logs directory: {logs_dir} (not writable)")
                paths_ok = False
        else:
            print(f"  ⚠️  Logs directory: {logs_dir} (will be created)")
            self.warnings.append(f"Logs directory {logs_dir} will be created on startup")
        
        return paths_ok
    
    def check_models_directory(self) -> bool:
        """Check if models directory exists and contains models."""
        try:
            models_dir = path_manager.get_models_dir()
        except:
            models_dir = path_manager.config.get("models", {}).get("models_dir")
            if models_dir:
                models_dir = Path(models_dir).expanduser()
            else:
                self.warnings.append("No models directory configured")
                print("  ⚠️  Models directory: Not configured in config.toml")
                return False
        
        if not models_dir.exists():
            self.warnings.append(f"Models directory {models_dir} does not exist")
            print(f"  ⚠️  Models directory: {models_dir} (not found)")
            return False
        
        # Check for .gguf files
        gguf_files = list(models_dir.rglob("*.gguf"))
        if gguf_files:
            print(f"  ✅ Models directory: {models_dir} ({len(gguf_files)} model(s) found)")
            for model in gguf_files[:3]:  # Show first 3
                print(f"     - {model.name}")
            if len(gguf_files) > 3:
                print(f"     ... and {len(gguf_files) - 3} more")
        else:
            self.warnings.append(f"No .gguf models found in {models_dir}")
            print(f"  ⚠️  Models directory: {models_dir} (no .gguf files)")
        
        return True
    
    def check_docker(self) -> bool:
        """Check if Docker is installed and running."""
        # Check if docker command exists
        if not shutil.which("docker"):
            self.errors.append("Docker is not installed")
            print("  ❌ Docker: Not installed")
            return False
        
        # Check if Docker daemon is running
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print("  ✅ Docker: Installed and running")
                return True
            else:
                self.errors.append("Docker is installed but not running")
                print("  ❌ Docker: Installed but not running")
                return False
        except subprocess.TimeoutExpired:
            self.errors.append("Docker command timeout (daemon not responding)")
            print("  ❌ Docker: Not responding")
            return False
        except Exception as e:
            self.errors.append(f"Docker check failed: {e}")
            print(f"  ❌ Docker: Check failed ({e})")
            return False
    
    def check_disk_space(self, min_gb: int = 10) -> bool:
        """
        Check available disk space on storage_root.
        
        Args:
            min_gb: Minimum required space in GB
        """
        storage_root = path_manager.get_storage_root()
        
        # Get parent if storage_root doesn't exist yet
        check_path = storage_root if storage_root.exists() else storage_root.parent
        
        try:
            stat = shutil.disk_usage(check_path)
            free_gb = stat.free / (1024**3)
            
            if free_gb >= min_gb:
                print(f"  ✅ Disk space: {free_gb:.1f} GB available (min: {min_gb} GB)")
                return True
            else:
                self.warnings.append(f"Low disk space: {free_gb:.1f} GB (recommended: {min_gb} GB)")
                print(f"  ⚠️  Disk space: {free_gb:.1f} GB available (low)")
                return False
        except Exception as e:
            self.warnings.append(f"Could not check disk space: {e}")
            print(f"  ⚠️  Disk space: Check failed ({e})")
            return False
    
    def check_python_packages(self) -> bool:
        """Check if required Python packages are installed."""
        required_packages = [
            "toml",
            "lancedb",
            "requests",
            "uvicorn",
            "fastapi"
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            self.errors.append(f"Missing Python packages: {', '.join(missing)}")
            print(f"  ❌ Python packages: Missing {', '.join(missing)}")
            print(f"     Run: pip install {' '.join(missing)}")
            return False
        else:
            print(f"  ✅ Python packages: All required packages installed")
            return True
    
    def run_all_checks(self) -> bool:
        """
        Run all compatibility checks.
        
        Returns:
            True if all critical checks pass, False otherwise
        """
        print("\n🔍 AI Tao - System Compatibility Check\n")
        print("=" * 60)
        
        all_ok = True
        
        # 1. Port availability
        print("\n📡 Network Ports:")
        api_port = self.config.get("server", {}).get("api_port", 8247)
        ui_port = self.config.get("server", {}).get("ui_port", 3001)
        
        if not self.check_port_available(api_port, "API Server"):
            all_ok = False
        if not self.check_port_available(ui_port, "AnythingLLM UI"):
            all_ok = False
        
        # 2. Storage paths
        print("\n📂 Storage & Paths:")
        if not self.check_storage_paths():
            all_ok = False
        
        # 3. Models directory
        print("\n🤖 AI Models:")
        self.check_models_directory()  # Non-blocking
        
        # 4. Docker
        print("\n🐳 Docker:")
        if not self.check_docker():
            all_ok = False
        
        # 5. Disk space
        print("\n💾 Disk Space:")
        self.check_disk_space(min_gb=10)  # Non-blocking
        
        # 6. Python packages
        print("\n🐍 Python Environment:")
        if not self.check_python_packages():
            all_ok = False
        
        # Summary
        print("\n" + "=" * 60)
        print("\n📊 Summary:\n")
        
        if self.errors:
            print("❌ Critical Errors:")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ All checks passed! System is ready.")
        elif not self.errors:
            print("\n✅ Critical checks passed (warnings can be ignored)")
        else:
            print("\n❌ System not ready. Fix errors above before starting.")
        
        print("\n" + "=" * 60 + "\n")
        
        return all_ok


def main():
    """Main entry point."""
    checker = CompatibilityChecker()
    
    try:
        success = checker.run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Check interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
