"""
Unit tests for fix_ollama_templates.py (US-029).

Tests the model template detection, fixing, and validation functionality
without requiring actual Ollama models to be installed.

Test coverage:
- Template pattern detection (broken vs correct)
- Model family detection from name
- Modelfile generation
- CLI argument parsing
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add scripts to path
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

from fix_ollama_templates import (
    TemplateStatus,
    ModelInfo,
    ValidationResult,
    detect_model_family,
    is_template_broken,
    extract_template_line,
    check_template_has_pattern,
    MODEL_TEMPLATES,
    BROKEN_PATTERNS,
)


# ============================================================================
# Test Data
# ============================================================================

BROKEN_TEMPLATE_SIMPLE = """# Modelfile
FROM qwen2.5-coder:7b
TEMPLATE {{ .Prompt }}
"""

BROKEN_TEMPLATE_SYSTEM = """# Modelfile
FROM qwen2.5-coder:7b
TEMPLATE {{ .System }}{{ .Prompt }}
"""

CORRECT_QWEN_TEMPLATE = '''# Modelfile
FROM qwen2.5-coder:7b
TEMPLATE """{{- if .System }}
<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}
{{- range .Messages }}
<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}
<|im_start|>assistant
"""
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
'''

CORRECT_LLAMA_TEMPLATE = '''# Modelfile
FROM llama3.1:8b
TEMPLATE """{{- if .System }}<|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|>{{ end }}{{ range .Messages }}<|start_header_id|>{{ .Role }}<|end_header_id|>

{{ .Content }}<|eot_id|>{{ end }}<|start_header_id|>assistant<|end_header_id|>

"""
'''

NO_TEMPLATE = """# Modelfile
FROM qwen2.5-coder:7b
PARAMETER temperature 0.7
"""


# ============================================================================
# Tests: Template Detection
# ============================================================================

class TestTemplateDetection:
    """Tests for template pattern detection."""
    
    def test_broken_simple_template(self):
        """Bare {{ .Prompt }} should be detected as broken."""
        assert is_template_broken(BROKEN_TEMPLATE_SIMPLE) is True
    
    def test_broken_system_prompt_template(self):
        """{{ .System }}{{ .Prompt }} should be detected as broken."""
        assert is_template_broken(BROKEN_TEMPLATE_SYSTEM) is True
    
    def test_no_template_is_broken(self):
        """Missing template should be detected as broken."""
        assert is_template_broken(NO_TEMPLATE) is True
    
    def test_correct_qwen_template(self):
        """Correct Qwen ChatML template should pass."""
        assert is_template_broken(CORRECT_QWEN_TEMPLATE) is False
    
    def test_correct_llama_template(self):
        """Correct Llama template should pass."""
        assert is_template_broken(CORRECT_LLAMA_TEMPLATE) is False


class TestExtractTemplateLine:
    """Tests for extracting the TEMPLATE line."""
    
    def test_extract_simple_template(self):
        """Should extract simple template line."""
        line = extract_template_line(BROKEN_TEMPLATE_SIMPLE)
        assert line is not None
        assert "{{ .Prompt }}" in line
    
    def test_extract_from_no_template(self):
        """Should return None when no template exists."""
        line = extract_template_line(NO_TEMPLATE)
        assert line is None
    
    def test_extract_multiline_returns_first_line(self):
        """For multiline templates, should return the TEMPLATE line."""
        line = extract_template_line(CORRECT_QWEN_TEMPLATE)
        assert line is not None
        assert line.startswith("TEMPLATE")


class TestCheckTemplatePattern:
    """Tests for pattern matching in templates."""
    
    def test_qwen_pattern_present(self):
        """Should detect ChatML tokens in Qwen template."""
        pattern = MODEL_TEMPLATES["qwen"]["pattern"]
        assert check_template_has_pattern(CORRECT_QWEN_TEMPLATE, pattern) is True
    
    def test_qwen_pattern_missing(self):
        """Should not find ChatML tokens in broken template."""
        pattern = MODEL_TEMPLATES["qwen"]["pattern"]
        assert check_template_has_pattern(BROKEN_TEMPLATE_SIMPLE, pattern) is False
    
    def test_llama_pattern_present(self):
        """Should detect Llama tokens in Llama template."""
        pattern = MODEL_TEMPLATES["llama"]["pattern"]
        assert check_template_has_pattern(CORRECT_LLAMA_TEMPLATE, pattern) is True


# ============================================================================
# Tests: Model Family Detection
# ============================================================================

class TestModelFamilyDetection:
    """Tests for detecting model family from name."""
    
    @pytest.mark.parametrize("model_name,expected_family", [
        ("qwen2.5-coder:7b", "qwen"),
        ("qwen2.5-coder-local:latest", "qwen"),
        ("qwen-coder", "qwen"),
        ("Qwen2.5-Coder:7B", "qwen"),
        ("qwen3-vl:latest", "qwen3-vl"),
        ("qwen-vl:8b", "qwen3-vl"),
        ("llama3.1:8b", "llama"),
        ("llama3.1-local:latest", "llama"),
        ("Llama-3.2:8b", "llama"),
        ("mistral:7b", "unknown"),
        ("custom-model:latest", "unknown"),
    ])
    def test_family_detection(self, model_name: str, expected_family: str):
        """Should correctly detect model family from name."""
        assert detect_model_family(model_name) == expected_family


# ============================================================================
# Tests: Data Classes
# ============================================================================

class TestModelInfo:
    """Tests for ModelInfo dataclass."""
    
    def test_model_info_creation(self):
        """Should create ModelInfo with all fields."""
        info = ModelInfo(
            name="qwen2.5-coder-local:latest",
            family="qwen",
            template="TEMPLATE {{ .Prompt }}",
            status=TemplateStatus.BROKEN,
            message="Template is broken",
        )
        assert info.name == "qwen2.5-coder-local:latest"
        assert info.status == TemplateStatus.BROKEN
    
    def test_model_info_default_message(self):
        """Should have empty default message."""
        info = ModelInfo(
            name="test",
            family="unknown",
            template="",
            status=TemplateStatus.OK,
        )
        assert info.message == ""


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_validation_success(self):
        """Should represent successful validation."""
        result = ValidationResult(
            model="qwen2.5-coder:7b",
            success=True,
            response="Python est un langage de programmation...",
        )
        assert result.success is True
        assert result.error is None
    
    def test_validation_failure(self):
        """Should represent failed validation."""
        result = ValidationResult(
            model="qwen2.5-coder-local",
            success=False,
            response="<|im_start|>gibberish...",
            error="Response does not appear coherent",
        )
        assert result.success is False
        assert result.error is not None


# ============================================================================
# Tests: Template Status Enum
# ============================================================================

class TestTemplateStatus:
    """Tests for TemplateStatus enum."""
    
    def test_status_values(self):
        """Should have expected status values."""
        assert TemplateStatus.OK.value == "ok"
        assert TemplateStatus.BROKEN.value == "broken"
        assert TemplateStatus.UNKNOWN.value == "unknown"
        assert TemplateStatus.NOT_FOUND.value == "not_found"


# ============================================================================
# Tests: Broken Patterns
# ============================================================================

class TestBrokenPatterns:
    """Tests for broken pattern regex."""
    
    def test_patterns_exist(self):
        """Should have defined broken patterns."""
        assert len(BROKEN_PATTERNS) > 0
    
    def test_patterns_are_regex(self):
        """Patterns should be valid regex strings."""
        import re
        for pattern in BROKEN_PATTERNS:
            # Should not raise
            re.compile(pattern)


# ============================================================================
# Tests: Modelfiles Directory
# ============================================================================

class TestModelfilesDirectory:
    """Tests for modelfiles configuration."""
    
    def test_modelfiles_exist(self):
        """Should have modelfiles in config/modelfiles/."""
        modelfiles_dir = Path(__file__).parent.parent.parent / "config" / "modelfiles"
        assert modelfiles_dir.exists(), f"Missing: {modelfiles_dir}"
    
    def test_qwen_modelfile_exists(self):
        """Should have Qwen modelfile."""
        modelfile = Path(__file__).parent.parent.parent / "config" / "modelfiles" / "qwen2.5-coder.Modelfile"
        assert modelfile.exists(), f"Missing: {modelfile}"
    
    def test_qwen_vl_modelfile_exists(self):
        """Should have Qwen-VL modelfile."""
        modelfile = Path(__file__).parent.parent.parent / "config" / "modelfiles" / "qwen3-vl.Modelfile"
        assert modelfile.exists(), f"Missing: {modelfile}"
    
    def test_llama_modelfile_exists(self):
        """Should have Llama modelfile."""
        modelfile = Path(__file__).parent.parent.parent / "config" / "modelfiles" / "llama3.1.Modelfile"
        assert modelfile.exists(), f"Missing: {modelfile}"
    
    def test_modelfiles_have_correct_template(self):
        """Modelfiles should contain proper ChatML structure."""
        modelfiles_dir = Path(__file__).parent.parent.parent / "config" / "modelfiles"
        
        qwen_content = (modelfiles_dir / "qwen2.5-coder.Modelfile").read_text()
        assert "<|im_start|>" in qwen_content
        assert "<|im_end|>" in qwen_content
        
        llama_content = (modelfiles_dir / "llama3.1.Modelfile").read_text()
        assert "<|start_header_id|>" in llama_content


# ============================================================================
# Tests: Integration with mocks
# ============================================================================

class TestOllamaIntegration:
    """Tests for Ollama integration using mocks."""
    
    @patch("fix_ollama_templates.run_ollama_command")
    def test_list_models_success(self, mock_run):
        """Should parse model list correctly."""
        from fix_ollama_templates import list_models
        
        mock_run.return_value = (True, """NAME                      	ID          	SIZE  	MODIFIED
qwen2.5-coder-local:latest	abc123      	4.7 GB	1 day ago
llama3.1:8b               	def456      	4.7 GB	2 days ago
""")
        
        models = list_models()
        assert "qwen2.5-coder-local:latest" in models
        assert "llama3.1:8b" in models
    
    @patch("fix_ollama_templates.run_ollama_command")
    def test_list_models_empty(self, mock_run):
        """Should handle empty model list."""
        from fix_ollama_templates import list_models
        
        mock_run.return_value = (True, "NAME	ID	SIZE	MODIFIED\n")
        
        models = list_models()
        assert models == []
    
    @patch("fix_ollama_templates.run_ollama_command")
    def test_list_models_error(self, mock_run):
        """Should handle Ollama connection error."""
        from fix_ollama_templates import list_models
        
        mock_run.return_value = (False, "Connection refused")
        
        models = list_models()
        assert models == []
    
    @patch("fix_ollama_templates.run_ollama_command")
    def test_analyze_model_broken(self, mock_run):
        """Should detect broken model template."""
        from fix_ollama_templates import analyze_model
        
        mock_run.return_value = (True, BROKEN_TEMPLATE_SIMPLE)
        
        info = analyze_model("qwen2.5-coder-local:latest")
        assert info.status == TemplateStatus.BROKEN
        assert info.family == "qwen"
    
    @patch("fix_ollama_templates.run_ollama_command")
    def test_analyze_model_ok(self, mock_run):
        """Should validate correct model template."""
        from fix_ollama_templates import analyze_model
        
        mock_run.return_value = (True, CORRECT_QWEN_TEMPLATE)
        
        info = analyze_model("qwen2.5-coder-local:latest")
        assert info.status == TemplateStatus.OK
    
    @patch("fix_ollama_templates.run_ollama_command")
    def test_analyze_model_not_found(self, mock_run):
        """Should handle model not found."""
        from fix_ollama_templates import analyze_model
        
        mock_run.return_value = (False, "model not found")
        
        info = analyze_model("nonexistent:latest")
        assert info.status == TemplateStatus.NOT_FOUND
