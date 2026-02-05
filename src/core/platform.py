"""
Platform Detection Module for AiTao.

This module detects hardware and software capabilities at runtime to enable
platform-specific optimizations, particularly for Apple Silicon with MLX.

Key Features:
- Detect OS (macOS, Linux, Windows)
- Detect architecture (arm64, x86_64)
- Detect Apple Silicon + Metal support
- Detect MLX availability and functionality
- Singleton pattern with caching (no re-detection)

Usage:
    from src.core.platform import get_platform_info, PlatformInfo
    
    info = get_platform_info()
    if info.has_mlx:
        # Use MLX-accelerated inference
        pass

Conformity:
- NFR-001: Platform Support (macOS Apple Silicon M1+ priority)
- NFR-005: Maintainability (<400 lines, file header, JSON logging)
"""

import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from src.core.logger import get_logger

logger = get_logger("core.platform")


# ============================================================================
# Platform Information Dataclass
# ============================================================================

@dataclass(frozen=True)
class PlatformInfo:
    """
    Immutable platform information detected at startup.
    
    Attributes:
        os: Operating system name (macOS, Linux, Windows)
        arch: CPU architecture (arm64, x86_64)
        is_apple_silicon: True if running on Apple Silicon (M1/M2/M3)
        has_metal: True if Metal GPU framework is available
        has_mlx: True if MLX is importable and functional
        cpu_cores: Number of CPU cores
        memory_gb: Total system memory in gigabytes
        python_version: Python version string
        mlx_version: MLX version if available, None otherwise
    """
    os: str
    arch: str
    is_apple_silicon: bool
    has_metal: bool
    has_mlx: bool
    cpu_cores: int
    memory_gb: float
    python_version: str
    mlx_version: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON logging."""
        return {
            "os": self.os,
            "arch": self.arch,
            "is_apple_silicon": self.is_apple_silicon,
            "has_metal": self.has_metal,
            "has_mlx": self.has_mlx,
            "cpu_cores": self.cpu_cores,
            "memory_gb": round(self.memory_gb, 2),
            "python_version": self.python_version,
            "mlx_version": self.mlx_version,
        }
    
    def supports_mlx_acceleration(self) -> bool:
        """Check if platform supports MLX-accelerated inference."""
        return self.is_apple_silicon and self.has_mlx and self.has_metal
    
    def get_recommended_backend(self) -> str:
        """
        Get recommended LLM backend based on platform capabilities.
        
        Returns:
            'mlx' if MLX acceleration is available
            'ollama' as fallback for all platforms
        """
        if self.supports_mlx_acceleration():
            return "mlx"
        return "ollama"


# ============================================================================
# Detection Functions
# ============================================================================

def _detect_os() -> str:
    """Detect operating system name."""
    system = platform.system()
    if system == "Darwin":
        return "macOS"
    return system  # Linux, Windows


def _detect_arch() -> str:
    """Detect CPU architecture."""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    return machine


def _detect_apple_silicon() -> bool:
    """
    Detect if running on Apple Silicon (M1/M2/M3/M4).
    
    Returns True only on macOS with arm64 architecture.
    """
    return _detect_os() == "macOS" and _detect_arch() == "arm64"


def _detect_metal() -> bool:
    """
    Detect if Metal GPU framework is available.
    
    Metal is only available on macOS. We check by trying to import
    the Metal framework via PyObjC or by checking system info.
    """
    if _detect_os() != "macOS":
        return False
    
    # On macOS arm64, Metal is always available
    if _detect_apple_silicon():
        return True
    
    # On Intel Macs, check for Metal support via system_profiler
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "Metal" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _detect_mlx() -> tuple[bool, Optional[str]]:
    """
    Detect if MLX is importable and functional.
    
    Returns:
        Tuple of (is_available, version_string)
    """
    if not _detect_apple_silicon():
        # MLX only works on Apple Silicon
        return False, None
    
    try:
        import mlx.core as mx
        
        # Verify MLX is functional by doing a simple operation
        test_array = mx.array([1.0, 2.0, 3.0])
        result = mx.sum(test_array)
        mx.eval(result)  # Force evaluation
        
        # Get version
        try:
            import mlx
            version = getattr(mlx, "__version__", "unknown")
        except Exception:
            version = "unknown"
        
        return True, version
        
    except ImportError:
        logger.debug("MLX not installed")
        return False, None
    except Exception as e:
        logger.warning(f"MLX installed but not functional: {e}")
        return False, None


def _detect_cpu_cores() -> int:
    """Detect number of CPU cores."""
    try:
        # os.cpu_count() includes hyperthreading
        return os.cpu_count() or 1
    except Exception:
        return 1


def _detect_memory_gb() -> float:
    """Detect total system memory in gigabytes."""
    try:
        if _detect_os() == "macOS":
            # Use sysctl on macOS
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            bytes_mem = int(result.stdout.strip())
            return bytes_mem / (1024 ** 3)
        
        elif _detect_os() == "Linux":
            # Read from /proc/meminfo
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
            return 0.0
        
        elif _detect_os() == "Windows":
            # Use wmic on Windows
            result = subprocess.run(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                bytes_mem = int(lines[1].strip())
                return bytes_mem / (1024 ** 3)
            return 0.0
        
        return 0.0
        
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        return 0.0


def _detect_python_version() -> str:
    """Get Python version string."""
    return platform.python_version()


# ============================================================================
# Singleton Pattern
# ============================================================================

_platform_info: Optional[PlatformInfo] = None


def get_platform_info() -> PlatformInfo:
    """
    Get platform information singleton.
    
    Detection is performed once at first call, then cached.
    Subsequent calls return the cached instance.
    
    Returns:
        PlatformInfo instance with all detected capabilities.
    """
    global _platform_info
    
    if _platform_info is None:
        logger.info("Detecting platform capabilities...")
        
        detected_os = _detect_os()
        detected_arch = _detect_arch()
        is_apple_silicon = _detect_apple_silicon()
        has_metal = _detect_metal()
        has_mlx, mlx_version = _detect_mlx()
        cpu_cores = _detect_cpu_cores()
        memory_gb = _detect_memory_gb()
        python_version = _detect_python_version()
        
        _platform_info = PlatformInfo(
            os=detected_os,
            arch=detected_arch,
            is_apple_silicon=is_apple_silicon,
            has_metal=has_metal,
            has_mlx=has_mlx,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            python_version=python_version,
            mlx_version=mlx_version,
        )
        
        # Log detected capabilities
        logger.info(
            "Platform detection complete",
            metadata=_platform_info.to_dict(),
        )
        
        # Log recommendations
        if _platform_info.supports_mlx_acceleration():
            logger.info(
                "MLX acceleration available",
                metadata={"recommended_backend": "mlx", "mlx_version": mlx_version},
            )
        else:
            logger.info(
                "Using Ollama backend",
                metadata={"recommended_backend": "ollama", "reason": _get_fallback_reason(_platform_info)},
            )
    
    return _platform_info


def _get_fallback_reason(info: PlatformInfo) -> str:
    """Get human-readable reason for Ollama fallback."""
    if info.os != "macOS":
        return f"Not macOS (running {info.os})"
    if info.arch != "arm64":
        return f"Not Apple Silicon (arch: {info.arch})"
    if not info.has_mlx:
        return "MLX not installed or not functional"
    if not info.has_metal:
        return "Metal not available"
    return "Unknown"


def reset_platform_info() -> None:
    """
    Reset the platform info singleton.
    
    Useful for testing with mocked detection functions.
    """
    global _platform_info
    _platform_info = None
    logger.debug("Platform info reset")


# ============================================================================
# Convenience Functions
# ============================================================================

def is_apple_silicon() -> bool:
    """Quick check for Apple Silicon."""
    return get_platform_info().is_apple_silicon


def has_mlx_support() -> bool:
    """Quick check for MLX support."""
    return get_platform_info().supports_mlx_acceleration()


def get_recommended_backend() -> str:
    """Get recommended LLM backend for this platform."""
    return get_platform_info().get_recommended_backend()
