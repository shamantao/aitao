#!/usr/bin/env python3
"""
Ollama Model Template Fixer and Validator.

This script detects and fixes broken Ollama model templates, particularly for Qwen models
that may have been imported with incomplete ChatML templates. It also validates templates
for newly pulled models and provides a health check endpoint.

Responsibilities:
- Detect models with broken templates (e.g., bare {{ .Prompt }})
- Apply correct ChatML templates from config/modelfiles/
- Validate model responses with a simple test prompt
- Provide CLI commands for model management

Usage:
    python scripts/fix_ollama_templates.py --check          # Check all models
    python scripts/fix_ollama_templates.py --fix            # Fix broken models
    python scripts/fix_ollama_templates.py --validate       # Run validation tests
    python scripts/fix_ollama_templates.py --model qwen2.5-coder-local  # Fix specific model
"""

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from core.logger import get_logger
except ImportError:
    # Fallback if logger not available
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    def get_logger(name: str):
        return logging.getLogger(name)

logger = get_logger("fix_ollama_templates")


# ============================================================================
# Constants and Configuration
# ============================================================================

MODELFILES_DIR = Path(__file__).parent.parent / "config" / "modelfiles"

# Known model families and their expected template patterns
MODEL_TEMPLATES = {
    "qwen": {
        "pattern": r"<\|im_start\|>",  # ChatML pattern
        "modelfile": "qwen2.5-coder.Modelfile",
    },
    "qwen3-vl": {
        "pattern": r"<\|im_start\|>",
        "modelfile": "qwen3-vl.Modelfile",
    },
    "llama": {
        "pattern": r"<\|start_header_id\|>",
        "modelfile": "llama3.1.Modelfile",
    },
}

# Broken template patterns that indicate a problem
BROKEN_PATTERNS = [
    r"^TEMPLATE\s*\{\{\s*\.Prompt\s*\}\}\s*$",  # Bare {{ .Prompt }}
    r"^TEMPLATE\s*\{\{\s*\.System\s*\}\}.*\{\{\s*\.Prompt\s*\}\}\s*$",  # {{ .System }}{{ .Prompt }}
]

# Test prompt for validation
VALIDATION_PROMPT = "Réponds en une seule phrase: qu'est-ce que Python?"
EXPECTED_KEYWORDS = ["langage", "programmation", "language", "programming", "python"]


class TemplateStatus(str, Enum):
    """Status of a model's template."""
    OK = "ok"
    BROKEN = "broken"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"


@dataclass
class ModelInfo:
    """Information about an Ollama model."""
    name: str
    family: str
    template: str
    status: TemplateStatus
    message: str = ""


@dataclass
class ValidationResult:
    """Result of validating a model with a test prompt."""
    model: str
    success: bool
    response: str
    error: Optional[str] = None


# ============================================================================
# Ollama Interaction
# ============================================================================

def run_ollama_command(args: list[str], timeout: int = 30) -> tuple[bool, str]:
    """
    Run an ollama command and return success status and output.
    
    Args:
        args: Command arguments (without 'ollama' prefix)
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            ["ollama"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, "Ollama not found. Is it installed?"
    except Exception as e:
        return False, str(e)


def list_models() -> list[str]:
    """Get list of installed Ollama models."""
    success, output = run_ollama_command(["list"])
    if not success:
        logger.error(f"Failed to list models: {output}")
        return []
    
    models = []
    for line in output.split("\n")[1:]:  # Skip header
        if line.strip():
            # Format: NAME    ID    SIZE    MODIFIED
            parts = line.split()
            if parts:
                models.append(parts[0])
    return models


def get_model_template(model_name: str) -> Optional[str]:
    """Get the template of a model from its modelfile."""
    success, output = run_ollama_command(["show", model_name, "--modelfile"])
    if not success:
        return None
    return output


def detect_model_family(model_name: str) -> str:
    """Detect the model family from the model name."""
    name_lower = model_name.lower()
    
    if "qwen3-vl" in name_lower or "qwen-vl" in name_lower:
        return "qwen3-vl"
    elif "qwen" in name_lower:
        return "qwen"
    elif "llama" in name_lower:
        return "llama"
    else:
        return "unknown"


# ============================================================================
# Template Analysis
# ============================================================================

def extract_template_line(modelfile: str) -> Optional[str]:
    """Extract the TEMPLATE line from a modelfile."""
    for line in modelfile.split("\n"):
        if line.strip().startswith("TEMPLATE"):
            return line.strip()
    return None


def is_template_broken(modelfile: str) -> bool:
    """Check if the template is broken (too simple)."""
    template_line = extract_template_line(modelfile)
    if not template_line:
        return True  # No template = broken
    
    for pattern in BROKEN_PATTERNS:
        if re.match(pattern, template_line, re.IGNORECASE):
            return True
    
    # Check if it's a multiline template (which is good)
    if '"""' in modelfile or "'''" in modelfile:
        return False
    
    # Single line template without proper tokens
    if "<|im_start|>" not in modelfile and "<|start_header_id|>" not in modelfile:
        return True
    
    return False


def check_template_has_pattern(modelfile: str, pattern: str) -> bool:
    """Check if modelfile contains the expected pattern."""
    return bool(re.search(pattern, modelfile))


def analyze_model(model_name: str) -> ModelInfo:
    """Analyze a model's template and return its status."""
    modelfile = get_model_template(model_name)
    if modelfile is None:
        return ModelInfo(
            name=model_name,
            family="unknown",
            template="",
            status=TemplateStatus.NOT_FOUND,
            message="Model not found or cannot read modelfile",
        )
    
    family = detect_model_family(model_name)
    
    if is_template_broken(modelfile):
        return ModelInfo(
            name=model_name,
            family=family,
            template=extract_template_line(modelfile) or "",
            status=TemplateStatus.BROKEN,
            message="Template is broken (missing ChatML structure)",
        )
    
    # Check family-specific patterns
    if family in MODEL_TEMPLATES:
        expected_pattern = MODEL_TEMPLATES[family]["pattern"]
        if not check_template_has_pattern(modelfile, expected_pattern):
            return ModelInfo(
                name=model_name,
                family=family,
                template=extract_template_line(modelfile) or "",
                status=TemplateStatus.BROKEN,
                message=f"Missing expected pattern: {expected_pattern}",
            )
    
    return ModelInfo(
        name=model_name,
        family=family,
        template=extract_template_line(modelfile) or "(multiline)",
        status=TemplateStatus.OK,
        message="Template looks correct",
    )


def check_all_models() -> list[ModelInfo]:
    """Check all installed models and return their status."""
    models = list_models()
    results = []
    
    for model in models:
        info = analyze_model(model)
        results.append(info)
        
        # Log status
        if info.status == TemplateStatus.OK:
            logger.info(f"✅ {model}: {info.message}")
        elif info.status == TemplateStatus.BROKEN:
            logger.warning(f"❌ {model}: {info.message}")
        else:
            logger.info(f"⚠️  {model}: {info.message}")
    
    return results


# ============================================================================
# Template Fixing
# ============================================================================

def get_modelfile_for_family(family: str) -> Optional[Path]:
    """Get the correct modelfile path for a model family."""
    if family in MODEL_TEMPLATES:
        modelfile_name = MODEL_TEMPLATES[family]["modelfile"]
        modelfile_path = MODELFILES_DIR / modelfile_name
        if modelfile_path.exists():
            return modelfile_path
    return None


def create_fixed_modelfile(model_name: str, family: str) -> Optional[str]:
    """Create a fixed modelfile content for a model."""
    # Get the original modelfile to extract FROM line
    original = get_model_template(model_name)
    if not original:
        return None
    
    # Extract the FROM line (base model)
    from_line = None
    for line in original.split("\n"):
        if line.strip().startswith("FROM"):
            from_line = line.strip()
            break
    
    if not from_line:
        logger.error(f"Cannot find FROM line in {model_name}")
        return None
    
    # Get the template modelfile
    template_path = get_modelfile_for_family(family)
    if not template_path:
        logger.error(f"No template modelfile found for family: {family}")
        return None
    
    # Read template and replace FROM line
    template_content = template_path.read_text()
    
    # Replace the FROM line with the original model's FROM
    lines = template_content.split("\n")
    new_lines = []
    for line in lines:
        if line.strip().startswith("FROM"):
            new_lines.append(from_line)
        else:
            new_lines.append(line)
    
    return "\n".join(new_lines)


def fix_model(model_name: str) -> bool:
    """
    Fix a model's template by recreating it with the correct template.
    
    Args:
        model_name: Name of the model to fix
        
    Returns:
        True if fix was successful
    """
    info = analyze_model(model_name)
    
    if info.status == TemplateStatus.OK:
        logger.info(f"Model {model_name} template is already OK")
        return True
    
    if info.status == TemplateStatus.NOT_FOUND:
        logger.error(f"Model {model_name} not found")
        return False
    
    # Create fixed modelfile
    fixed_content = create_fixed_modelfile(model_name, info.family)
    if not fixed_content:
        logger.error(f"Failed to create fixed modelfile for {model_name}")
        return False
    
    # Write to temp file and recreate model
    with tempfile.NamedTemporaryFile(mode="w", suffix=".Modelfile", delete=False) as f:
        f.write(fixed_content)
        temp_path = f.name
    
    try:
        logger.info(f"Recreating model {model_name} with fixed template...")
        success, output = run_ollama_command(
            ["create", model_name, "-f", temp_path],
            timeout=120,
        )
        
        if success:
            logger.info(f"✅ Successfully fixed {model_name}")
            return True
        else:
            logger.error(f"Failed to recreate model: {output}")
            return False
    finally:
        Path(temp_path).unlink(missing_ok=True)


def fix_all_broken_models() -> dict[str, bool]:
    """Fix all models with broken templates."""
    models = check_all_models()
    results = {}
    
    broken = [m for m in models if m.status == TemplateStatus.BROKEN]
    
    if not broken:
        logger.info("No broken models found!")
        return results
    
    logger.info(f"Found {len(broken)} broken model(s): {[m.name for m in broken]}")
    
    for model in broken:
        results[model.name] = fix_model(model.name)
    
    return results


# ============================================================================
# Validation
# ============================================================================

def validate_model(model_name: str, timeout: int = 60) -> ValidationResult:
    """
    Validate a model by sending a test prompt and checking the response.
    
    Args:
        model_name: Name of the model to validate
        timeout: Timeout in seconds for the response
        
    Returns:
        ValidationResult with success status and response
    """
    logger.info(f"Validating {model_name}...")
    
    success, response = run_ollama_command(
        ["run", model_name, VALIDATION_PROMPT],
        timeout=timeout,
    )
    
    if not success:
        return ValidationResult(
            model=model_name,
            success=False,
            response="",
            error=response,
        )
    
    # Check if response contains expected keywords
    response_lower = response.lower()
    has_expected = any(kw in response_lower for kw in EXPECTED_KEYWORDS)
    
    # Check for signs of hallucination/broken response
    is_coherent = (
        len(response) > 10 and
        len(response) < 2000 and
        not response.startswith("<|") and  # Leaking tokens
        has_expected
    )
    
    return ValidationResult(
        model=model_name,
        success=is_coherent,
        response=response[:500],  # Truncate for logging
        error=None if is_coherent else "Response does not appear coherent",
    )


def validate_all_models() -> list[ValidationResult]:
    """Validate all installed models."""
    models = list_models()
    results = []
    
    for model in models:
        result = validate_model(model)
        results.append(result)
        
        if result.success:
            logger.info(f"✅ {model}: Validation passed")
            logger.debug(f"   Response: {result.response[:100]}...")
        else:
            logger.warning(f"❌ {model}: Validation failed - {result.error}")
            if result.response:
                logger.warning(f"   Response: {result.response[:100]}...")
    
    return results


# ============================================================================
# CLI Interface
# ============================================================================

def print_status_report(models: list[ModelInfo]) -> None:
    """Print a formatted status report."""
    print("\n" + "=" * 60)
    print("OLLAMA MODEL TEMPLATE STATUS REPORT")
    print("=" * 60)
    
    ok = [m for m in models if m.status == TemplateStatus.OK]
    broken = [m for m in models if m.status == TemplateStatus.BROKEN]
    unknown = [m for m in models if m.status in (TemplateStatus.UNKNOWN, TemplateStatus.NOT_FOUND)]
    
    print(f"\n✅ OK: {len(ok)}")
    for m in ok:
        print(f"   - {m.name} ({m.family})")
    
    if broken:
        print(f"\n❌ BROKEN: {len(broken)}")
        for m in broken:
            print(f"   - {m.name} ({m.family}): {m.message}")
    
    if unknown:
        print(f"\n⚠️  UNKNOWN: {len(unknown)}")
        for m in unknown:
            print(f"   - {m.name}: {m.message}")
    
    print("\n" + "=" * 60)
    
    if broken:
        print("\n💡 Run with --fix to repair broken templates")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ollama Model Template Fixer and Validator"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check all models for template issues"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Fix all broken model templates"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate models with test prompts"
    )
    parser.add_argument(
        "--model", type=str,
        help="Target a specific model (with --fix or --validate)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    # Default to --check if no action specified
    if not any([args.check, args.fix, args.validate]):
        args.check = True
    
    if args.check:
        models = check_all_models()
        if args.json:
            print(json.dumps([{
                "name": m.name,
                "family": m.family,
                "status": m.status.value,
                "message": m.message,
            } for m in models], indent=2))
        else:
            print_status_report(models)
    
    elif args.fix:
        if args.model:
            success = fix_model(args.model)
            sys.exit(0 if success else 1)
        else:
            results = fix_all_broken_models()
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print("\nFix Results:")
                for model, success in results.items():
                    status = "✅" if success else "❌"
                    print(f"  {status} {model}")
            
            # Exit with error if any fix failed
            if not all(results.values()):
                sys.exit(1)
    
    elif args.validate:
        if args.model:
            result = validate_model(args.model)
            if args.json:
                print(json.dumps({
                    "model": result.model,
                    "success": result.success,
                    "response": result.response,
                    "error": result.error,
                }, indent=2))
            else:
                status = "✅ PASSED" if result.success else "❌ FAILED"
                print(f"{result.model}: {status}")
                if result.error:
                    print(f"  Error: {result.error}")
            sys.exit(0 if result.success else 1)
        else:
            results = validate_all_models()
            if args.json:
                print(json.dumps([{
                    "model": r.model,
                    "success": r.success,
                    "error": r.error,
                } for r in results], indent=2))
            else:
                print("\nValidation Results:")
                for r in results:
                    status = "✅" if r.success else "❌"
                    print(f"  {status} {r.model}")
            
            failed = [r for r in results if not r.success]
            if failed:
                sys.exit(1)


if __name__ == "__main__":
    main()
