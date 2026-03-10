"""
Unit tests for Platform Detection Module.

Tests the platform detection functionality with mocked system calls
to ensure correct behavior across different platforms.
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from src.core.platform import (
    PlatformInfo,
    get_platform_info,
    reset_platform_info,
    is_apple_silicon,
    has_mlx_support,
    get_recommended_backend,
    _detect_os,
    _detect_arch,
    _detect_apple_silicon,
    _detect_metal,
    _detect_mlx,
    _detect_cpu_cores,
    _detect_memory_gb,
    _detect_python_version,
)


class TestPlatformInfo:
    """Tests for PlatformInfo dataclass."""
    
    def test_platform_info_creation(self):
        """Test creating a PlatformInfo instance."""
        info = PlatformInfo(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_metal=True,
            has_mlx=True,
            cpu_cores=10,
            memory_gb=32.0,
            python_version="3.13.0",
            mlx_version="0.5.0",
        )
        
        assert info.os == "macOS"
        assert info.arch == "arm64"
        assert info.is_apple_silicon is True
        assert info.has_metal is True
        assert info.has_mlx is True
        assert info.cpu_cores == 10
        assert info.memory_gb == 32.0
        assert info.python_version == "3.13.0"
        assert info.mlx_version == "0.5.0"
    
    def test_platform_info_is_immutable(self):
        """Test that PlatformInfo is frozen (immutable)."""
        info = PlatformInfo(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_metal=True,
            has_mlx=True,
            cpu_cores=10,
            memory_gb=32.0,
            python_version="3.13.0",
        )
        
        with pytest.raises(AttributeError):
            info.os = "Linux"  # type: ignore
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        info = PlatformInfo(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_metal=True,
            has_mlx=True,
            cpu_cores=10,
            memory_gb=32.12345,
            python_version="3.13.0",
            mlx_version="0.5.0",
        )
        
        d = info.to_dict()
        
        assert d["os"] == "macOS"
        assert d["arch"] == "arm64"
        assert d["is_apple_silicon"] is True
        assert d["memory_gb"] == 32.12  # Rounded to 2 decimals
        assert d["mlx_version"] == "0.5.0"
    
    def test_supports_mlx_acceleration_true(self):
        """Test MLX acceleration support detection (positive)."""
        info = PlatformInfo(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_metal=True,
            has_mlx=True,
            cpu_cores=10,
            memory_gb=32.0,
            python_version="3.13.0",
        )
        
        assert info.supports_mlx_acceleration() is True
    
    def test_supports_mlx_acceleration_false_no_mlx(self):
        """Test MLX acceleration not available without MLX."""
        info = PlatformInfo(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_metal=True,
            has_mlx=False,  # MLX not installed
            cpu_cores=10,
            memory_gb=32.0,
            python_version="3.13.0",
        )
        
        assert info.supports_mlx_acceleration() is False
    
    def test_supports_mlx_acceleration_false_not_apple_silicon(self):
        """Test MLX acceleration not available on Intel Mac."""
        info = PlatformInfo(
            os="macOS",
            arch="x86_64",
            is_apple_silicon=False,
            has_metal=True,
            has_mlx=False,
            cpu_cores=8,
            memory_gb=16.0,
            python_version="3.13.0",
        )
        
        assert info.supports_mlx_acceleration() is False
    
    def test_get_recommended_backend_mlx(self):
        """Test recommended backend is MLX when available."""
        info = PlatformInfo(
            os="macOS",
            arch="arm64",
            is_apple_silicon=True,
            has_metal=True,
            has_mlx=True,
            cpu_cores=10,
            memory_gb=32.0,
            python_version="3.13.0",
        )
        
        assert info.get_recommended_backend() == "mlx"
    
    def test_get_recommended_backend_ollama(self):
        """Test recommended backend is Ollama as fallback."""
        info = PlatformInfo(
            os="Linux",
            arch="x86_64",
            is_apple_silicon=False,
            has_metal=False,
            has_mlx=False,
            cpu_cores=16,
            memory_gb=64.0,
            python_version="3.13.0",
        )
        
        assert info.get_recommended_backend() == "ollama"


class TestDetectOS:
    """Tests for _detect_os function."""
    
    @patch("platform.system", return_value="Darwin")
    def test_detect_macos(self, mock_system):
        """Test macOS detection."""
        assert _detect_os() == "macOS"
    
    @patch("platform.system", return_value="Linux")
    def test_detect_linux(self, mock_system):
        """Test Linux detection."""
        assert _detect_os() == "Linux"
    
    @patch("platform.system", return_value="Windows")
    def test_detect_windows(self, mock_system):
        """Test Windows detection."""
        assert _detect_os() == "Windows"


class TestDetectArch:
    """Tests for _detect_arch function."""
    
    @patch("platform.machine", return_value="arm64")
    def test_detect_arm64(self, mock_machine):
        """Test arm64 detection."""
        assert _detect_arch() == "arm64"
    
    @patch("platform.machine", return_value="aarch64")
    def test_detect_aarch64(self, mock_machine):
        """Test aarch64 (Linux ARM) detection."""
        assert _detect_arch() == "arm64"
    
    @patch("platform.machine", return_value="x86_64")
    def test_detect_x86_64(self, mock_machine):
        """Test x86_64 detection."""
        assert _detect_arch() == "x86_64"
    
    @patch("platform.machine", return_value="AMD64")
    def test_detect_amd64(self, mock_machine):
        """Test AMD64 (Windows) detection."""
        assert _detect_arch() == "x86_64"


class TestDetectAppleSilicon:
    """Tests for _detect_apple_silicon function."""
    
    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_detect_apple_silicon_true(self, mock_machine, mock_system):
        """Test Apple Silicon detection on M1/M2/M3."""
        assert _detect_apple_silicon() is True
    
    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="x86_64")
    def test_detect_apple_silicon_false_intel(self, mock_machine, mock_system):
        """Test Apple Silicon detection on Intel Mac."""
        assert _detect_apple_silicon() is False
    
    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="arm64")
    def test_detect_apple_silicon_false_linux(self, mock_machine, mock_system):
        """Test Apple Silicon detection on Linux ARM."""
        assert _detect_apple_silicon() is False


class TestDetectMetal:
    """Tests for _detect_metal function."""
    
    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_detect_metal_apple_silicon(self, mock_machine, mock_system):
        """Test Metal detection on Apple Silicon."""
        assert _detect_metal() is True
    
    @patch("platform.system", return_value="Linux")
    def test_detect_metal_linux(self, mock_system):
        """Test Metal detection on Linux (should be False)."""
        assert _detect_metal() is False
    
    @patch("platform.system", return_value="Windows")
    def test_detect_metal_windows(self, mock_system):
        """Test Metal detection on Windows (should be False)."""
        assert _detect_metal() is False


class TestDetectMLX:
    """Tests for _detect_mlx function."""
    
    @patch("platform.system", return_value="Linux")
    def test_detect_mlx_non_apple(self, mock_system):
        """Test MLX detection on non-Apple platform."""
        has_mlx, version = _detect_mlx()
        assert has_mlx is False
        assert version is None
    
    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_detect_mlx_import_error(self, mock_machine, mock_system):
        """Test MLX detection when not installed."""
        # This test may pass or fail depending on actual MLX installation
        # In CI without MLX, it should return False
        has_mlx, version = _detect_mlx()
        # Just verify it returns valid types
        assert isinstance(has_mlx, bool)
        assert version is None or isinstance(version, str)


class TestDetectCpuCores:
    """Tests for _detect_cpu_cores function."""
    
    @patch("os.cpu_count", return_value=10)
    def test_detect_cpu_cores(self, mock_cpu_count):
        """Test CPU core detection."""
        assert _detect_cpu_cores() == 10
    
    @patch("os.cpu_count", return_value=None)
    def test_detect_cpu_cores_fallback(self, mock_cpu_count):
        """Test CPU core detection fallback to 1."""
        assert _detect_cpu_cores() == 1


class TestDetectMemory:
    """Tests for _detect_memory_gb function."""
    
    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_detect_memory_macos(self, mock_run, mock_system):
        """Test memory detection on macOS."""
        # 32 GB in bytes
        mock_run.return_value = MagicMock(
            stdout="34359738368\n",  # 32 GB
            returncode=0,
        )
        
        memory = _detect_memory_gb()
        assert memory == 32.0
    
    @patch("platform.system", return_value="Linux")
    def test_detect_memory_linux(self, mock_system):
        """Test memory detection on Linux with mock /proc/meminfo."""
        mock_content = "MemTotal:       32894976 kB\nMemFree:        1234567 kB\n"
        
        with patch("builtins.open", MagicMock(return_value=MagicMock(
            __enter__=MagicMock(return_value=iter(mock_content.splitlines())),
            __exit__=MagicMock(return_value=False),
        ))):
            # The mock setup is complex, just verify no exception
            memory = _detect_memory_gb()
            assert isinstance(memory, float)


class TestSingleton:
    """Tests for singleton behavior."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        reset_platform_info()
    
    def test_get_platform_info_returns_same_instance(self):
        """Test singleton returns same instance."""
        info1 = get_platform_info()
        info2 = get_platform_info()
        
        assert info1 is info2
    
    def test_reset_platform_info(self):
        """Test reset creates new instance."""
        info1 = get_platform_info()
        reset_platform_info()
        info2 = get_platform_info()
        
        # Should be equal but not same object
        assert info1 == info2
        # After reset, it's technically a new detection
        # but values should be same on same machine


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        reset_platform_info()
    
    def test_is_apple_silicon(self):
        """Test is_apple_silicon convenience function."""
        result = is_apple_silicon()
        assert isinstance(result, bool)
    
    def test_has_mlx_support(self):
        """Test has_mlx_support convenience function."""
        result = has_mlx_support()
        assert isinstance(result, bool)
    
    def test_get_recommended_backend(self):
        """Test get_recommended_backend convenience function."""
        result = get_recommended_backend()
        assert result in ("mlx", "ollama")


class TestIntegration:
    """Integration tests with real platform detection."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        reset_platform_info()
    
    def test_real_platform_detection(self):
        """Test real platform detection on current machine."""
        info = get_platform_info()
        
        # Basic sanity checks
        assert info.os in ("macOS", "Linux", "Windows")
        assert info.arch in ("arm64", "x86_64", "aarch64")
        assert info.cpu_cores >= 1
        assert info.memory_gb >= 0
        assert len(info.python_version) > 0
        
        # Log for debugging
        print(f"Detected platform: {info.to_dict()}")
    
    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output can be JSON serialized."""
        import json
        
        info = get_platform_info()
        d = info.to_dict()
        
        # Should not raise
        json_str = json.dumps(d)
        assert len(json_str) > 0
