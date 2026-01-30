"""
Purpose: E2E test to validate config.yaml.template is synchronized with config.yaml.

This test ensures that:
1. All configuration keys in config.yaml exist in config.yaml.template
2. The template contains all required sections
3. Key values have sensible defaults

This helps maintain the template as a valid reference for new installations.
"""

import pytest
from pathlib import Path
from typing import Any, Set
import yaml


# =============================================================================
# Test Configuration
# =============================================================================

# Keys that can differ between template and actual config (user-specific values)
ALLOWED_DIFFERENT_VALUES = {
    "paths.storage_root",
    "paths.models_dir",
    "indexing.include_paths",
    "llm.default_model",
    "llm.models",
    # Legacy OCR provider - replaced by 'native' in V2
    "ocr.paddleocr",
}

# Required top-level sections that must exist in both files
REQUIRED_SECTIONS = [
    "paths",
    "worker",
    "indexing",
    "ocr",
    "translation",
    "search",
    "categories",
    "llm",
    "api",
    "resources",
    "logging",
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).resolve()
    # Navigate up from tests/e2e/ to project root
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root")


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten a nested dictionary into dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def get_all_keys(d: dict) -> Set[str]:
    """Extract all keys from a nested dictionary in dot notation."""
    return set(flatten_dict(d).keys())


def load_yaml_file(path: Path) -> dict:
    """Load a YAML file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# =============================================================================
# Tests
# =============================================================================

class TestConfigTemplate:
    """Test suite for config.yaml.template validation."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root path."""
        return get_project_root()
    
    @pytest.fixture
    def config_path(self, project_root: Path) -> Path:
        """Get path to config.yaml."""
        return project_root / "config" / "config.yaml"
    
    @pytest.fixture
    def template_path(self, project_root: Path) -> Path:
        """Get path to config.yaml.template."""
        return project_root / "config" / "config.yaml.template"
    
    @pytest.fixture
    def config_data(self, config_path: Path) -> dict:
        """Load config.yaml data."""
        if not config_path.exists():
            pytest.skip("config.yaml not found - run from configured environment")
        return load_yaml_file(config_path)
    
    @pytest.fixture
    def template_data(self, template_path: Path) -> dict:
        """Load config.yaml.template data."""
        if not template_path.exists():
            pytest.fail("config.yaml.template is missing!")
        return load_yaml_file(template_path)
    
    def test_template_exists(self, template_path: Path):
        """Verify config.yaml.template exists."""
        assert template_path.exists(), \
            f"Template file missing: {template_path}"
    
    def test_template_valid_yaml(self, template_data: dict):
        """Verify template is valid YAML."""
        assert isinstance(template_data, dict), \
            "Template is not a valid YAML dictionary"
    
    def test_required_sections_in_template(self, template_data: dict):
        """Verify all required sections exist in template."""
        missing_sections = []
        for section in REQUIRED_SECTIONS:
            if section not in template_data:
                missing_sections.append(section)
        
        assert not missing_sections, \
            f"Template missing required sections: {missing_sections}"
    
    def test_template_has_all_config_keys(
        self, 
        config_data: dict, 
        template_data: dict
    ):
        """Verify template contains all keys from config.yaml."""
        config_keys = get_all_keys(config_data)
        template_keys = get_all_keys(template_data)
        
        # Find keys in config but not in template
        missing_in_template = config_keys - template_keys
        
        # Filter out user-specific keys
        relevant_missing = {
            k for k in missing_in_template
            if not any(k.startswith(allowed) for allowed in ALLOWED_DIFFERENT_VALUES)
        }
        
        if relevant_missing:
            # Group by section for better error reporting
            sections = {}
            for key in sorted(relevant_missing):
                section = key.split(".")[0]
                if section not in sections:
                    sections[section] = []
                sections[section].append(key)
            
            error_msg = "Template missing keys from config.yaml:\n"
            for section, keys in sections.items():
                error_msg += f"\n  [{section}]\n"
                for key in keys:
                    error_msg += f"    - {key}\n"
            
            pytest.fail(error_msg)
    
    def test_template_api_port(self, template_data: dict):
        """Verify template has correct default API port."""
        api_config = template_data.get("api", {})
        port = api_config.get("port")
        
        assert port == 8200, \
            f"Template API port should be 8200, got {port}"
    
    def test_template_llm_section_complete(self, template_data: dict):
        """Verify LLM section has all required subsections."""
        llm_config = template_data.get("llm", {})
        
        required_llm_keys = [
            "backend",
            "ollama_url", 
            "default_model",
            "models",
            "startup",
            "rag",
            "generation",
        ]
        
        missing_llm = [k for k in required_llm_keys if k not in llm_config]
        
        assert not missing_llm, \
            f"Template llm section missing keys: {missing_llm}"
    
    def test_template_ocr_router_config(self, template_data: dict):
        """Verify OCR router configuration exists."""
        ocr_config = template_data.get("ocr", {})
        
        assert "router" in ocr_config, \
            "Template ocr section missing 'router' subsection"
        assert "native" in ocr_config, \
            "Template ocr section missing 'native' subsection"
    
    def test_template_meilisearch_url(self, template_data: dict):
        """Verify Meilisearch URL is correctly configured."""
        search_config = template_data.get("search", {})
        meili_config = search_config.get("meilisearch", {})
        
        url = meili_config.get("url")
        assert url == "http://localhost:7700", \
            f"Template Meilisearch URL should be http://localhost:7700, got {url}"
    
    def test_template_ollama_url(self, template_data: dict):
        """Verify Ollama URL is correctly configured."""
        llm_config = template_data.get("llm", {})
        
        url = llm_config.get("ollama_url")
        assert url == "http://localhost:11434", \
            f"Template Ollama URL should be http://localhost:11434, got {url}"


# =============================================================================
# Standalone Comparison Script
# =============================================================================

def compare_configs() -> dict:
    """
    Compare config.yaml and config.yaml.template.
    
    Returns a dict with:
        - missing_in_template: keys in config but not in template
        - extra_in_template: keys in template but not in config
        - differences: keys with different values (excluding allowed)
    """
    project_root = get_project_root()
    config_path = project_root / "config" / "config.yaml"
    template_path = project_root / "config" / "config.yaml.template"
    
    result = {
        "config_exists": config_path.exists(),
        "template_exists": template_path.exists(),
        "missing_in_template": [],
        "extra_in_template": [],
        "section_comparison": {},
    }
    
    if not template_path.exists():
        result["error"] = "Template file not found"
        return result
    
    if not config_path.exists():
        result["warning"] = "config.yaml not found, cannot compare"
        return result
    
    config_data = load_yaml_file(config_path)
    template_data = load_yaml_file(template_path)
    
    config_keys = get_all_keys(config_data)
    template_keys = get_all_keys(template_data)
    
    result["missing_in_template"] = sorted(config_keys - template_keys)
    result["extra_in_template"] = sorted(template_keys - config_keys)
    
    # Compare by section
    all_sections = set(config_data.keys()) | set(template_data.keys())
    for section in sorted(all_sections):
        in_config = section in config_data
        in_template = section in template_data
        
        result["section_comparison"][section] = {
            "in_config": in_config,
            "in_template": in_template,
            "status": "ok" if (in_config and in_template) else "missing",
        }
    
    return result


def print_comparison_report():
    """Print a human-readable comparison report."""
    result = compare_configs()
    
    print("\n" + "=" * 60)
    print("  Config Template Comparison Report")
    print("=" * 60)
    
    # File status
    print("\nFile Status:")
    print(f"  config.yaml:          {'✓' if result['config_exists'] else '✗'}")
    print(f"  config.yaml.template: {'✓' if result['template_exists'] else '✗'}")
    
    # Section comparison
    print("\nSection Comparison:")
    for section, info in result.get("section_comparison", {}).items():
        config_mark = "✓" if info["in_config"] else "✗"
        template_mark = "✓" if info["in_template"] else "✗"
        print(f"  [{section}] config: {config_mark}  template: {template_mark}")
    
    # Missing keys
    missing = result.get("missing_in_template", [])
    if missing:
        print(f"\nKeys missing in template ({len(missing)}):")
        for key in missing[:20]:  # Limit output
            print(f"  - {key}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
    else:
        print("\n✓ No missing keys in template")
    
    # Extra keys
    extra = result.get("extra_in_template", [])
    if extra:
        print(f"\nExtra keys in template ({len(extra)}):")
        for key in extra[:10]:
            print(f"  + {key}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_comparison_report()
